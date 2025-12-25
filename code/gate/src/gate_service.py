"""
TheatreOS Gate System Service
Handles voting, staking, settlement, and Explain Card generation.

Key responsibilities:
- Create gate instances for slots
- Handle vote/stake submissions (idempotent)
- Resolve gates at designated time
- Generate Explain Cards
- Write outcomes to WorldState via Kernel
"""
import json
import hashlib
import logging
import uuid
import math
import secrets
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple
from decimal import Decimal, ROUND_DOWN

from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from kernel.src.database import (
    Theatre, HourPlan, get_db, Base, GUID, JSONType
)
from kernel.src.kernel_service import KernelService, ApplyDeltaRequest

# Import SQLAlchemy components for new models
from sqlalchemy import Column, String, Integer, BigInteger, Float, DateTime, Text, Boolean, ForeignKey, Numeric
from kernel.src.database import engine, SessionLocal

logger = logging.getLogger(__name__)


# =============================================================================
# Gate Models (SQLite Compatible)
# =============================================================================
class GateInstance(Base):
    """Gate instance - one per slot."""
    __tablename__ = "gate_instance"
    
    gate_instance_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    theatre_id = Column(GUID(), ForeignKey("theatre.theatre_id", ondelete="CASCADE"), nullable=False)
    slot_id = Column(Text, ForeignKey("hour_plan.slot_id", ondelete="CASCADE"), nullable=False)
    gate_template_id = Column(Text, nullable=False)
    type = Column(Text, nullable=False)  # Public/Fate/FateMajor/Council
    status = Column(Text, nullable=False, default="SCHEDULED")
    title = Column(Text, nullable=False)
    open_at = Column(DateTime, nullable=False)
    close_at = Column(DateTime, nullable=False)
    resolve_at = Column(DateTime, nullable=False)
    options_jsonb = Column(JSONType, nullable=False)
    base_prob_jsonb = Column(JSONType, nullable=True)
    random_seed = Column(BigInteger, nullable=True)
    winner_option_id = Column(Text, nullable=True)
    explain_card_jsonb = Column(JSONType, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class GateVote(Base):
    """Vote record - one per user per gate."""
    __tablename__ = "gate_vote"
    
    gate_instance_id = Column(GUID(), ForeignKey("gate_instance.gate_instance_id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Text, primary_key=True)
    option_id = Column(Text, nullable=False)
    ring_level = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    idempotency_key = Column(Text, nullable=False)


class GateStake(Base):
    """Stake record - one per user per currency per gate."""
    __tablename__ = "gate_stake"
    
    gate_instance_id = Column(GUID(), ForeignKey("gate_instance.gate_instance_id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Text, primary_key=True)
    currency = Column(Text, primary_key=True)
    option_id = Column(Text, nullable=False)
    amount_locked = Column(Numeric(18, 4), nullable=False, default=0)
    amount_final = Column(Numeric(18, 4), nullable=True)
    ring_level = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    idempotency_key = Column(Text, nullable=False)


class GateEvidenceSubmission(Base):
    """Evidence submission for a gate."""
    __tablename__ = "gate_evidence_submission"
    
    submission_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    gate_instance_id = Column(GUID(), ForeignKey("gate_instance.gate_instance_id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Text, nullable=False)
    evidence_instance_id = Column(Text, nullable=False)
    tier = Column(Text, nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    idempotency_key = Column(Text, nullable=False)


class GateSettlement(Base):
    """Settlement record for each user."""
    __tablename__ = "gate_settlement"
    
    gate_instance_id = Column(GUID(), ForeignKey("gate_instance.gate_instance_id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(Text, primary_key=True)
    currency = Column(Text, primary_key=True)
    stake = Column(Numeric(18, 4), nullable=False)
    payout = Column(Numeric(18, 4), nullable=False, default=0)
    fee_burn = Column(Numeric(18, 4), nullable=False, default=0)
    net_delta = Column(Numeric(18, 4), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class WalletBalance(Base):
    """User wallet balance."""
    __tablename__ = "wallet_balance"
    
    user_id = Column(Text, primary_key=True)
    currency = Column(Text, primary_key=True)
    balance = Column(Numeric(18, 4), nullable=False, default=0)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)


class WalletLedger(Base):
    """Wallet transaction ledger."""
    __tablename__ = "wallet_ledger"
    
    tx_id = Column(GUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(Text, nullable=False)
    currency = Column(Text, nullable=False)
    delta = Column(Numeric(18, 4), nullable=False)
    reason = Column(Text, nullable=False)
    ref_type = Column(Text, nullable=True)
    ref_id = Column(Text, nullable=True)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


# Create tables
Base.metadata.create_all(bind=engine)


# =============================================================================
# Configuration
# =============================================================================
GATE_FEE_RATE = Decimal("0.05")  # 5% burn fee
GATE_OPEN_DURATION_MINUTES = 2  # T+10 to T+12
GATE_RESOLVE_MINUTE = 12  # Resolve at T+12
GATE_EXPLAIN_DURATION_MINUTES = 3  # T+12 to T+15


# =============================================================================
# Data Transfer Objects
# =============================================================================
class VoteRequest:
    def __init__(self, option_id: str, ring_level: str = "C", idempotency_key: str = None):
        self.option_id = option_id
        self.ring_level = ring_level
        self.idempotency_key = idempotency_key or str(uuid.uuid4())


class StakeRequest:
    def __init__(self, option_id: str, currency: str, amount: Decimal, ring_level: str = "C", idempotency_key: str = None):
        self.option_id = option_id
        self.currency = currency
        self.amount = Decimal(str(amount))
        self.ring_level = ring_level
        self.idempotency_key = idempotency_key or str(uuid.uuid4())


class VoteResult:
    def __init__(self, success: bool, message: str, vote_id: str = None):
        self.success = success
        self.message = message
        self.vote_id = vote_id


class StakeResult:
    def __init__(self, success: bool, message: str, amount_locked: Decimal = None):
        self.success = success
        self.message = message
        self.amount_locked = amount_locked


class ResolveResult:
    def __init__(self, success: bool, winner_option_id: str = None, explain_card: Dict = None, error: str = None):
        self.success = success
        self.winner_option_id = winner_option_id
        self.explain_card = explain_card
        self.error = error


# =============================================================================
# Gate Service
# =============================================================================
class GateService:
    """
    Gate Service - The collective decision mechanism.
    
    Handles voting, staking, and settlement for hourly gates.
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # =========================================================================
    # Gate Instance Management
    # =========================================================================
    def create_gate_instance(
        self,
        theatre_id: str,
        slot_id: str,
        gate_config: Dict,
        slot_start_at: datetime
    ) -> GateInstance:
        """
        Create a gate instance for a slot.
        
        Called by Scene Delivery when publishing a slot.
        """
        theatre_uuid = uuid.UUID(theatre_id)
        
        # Check if gate already exists
        existing = self.db.query(GateInstance).filter(
            GateInstance.theatre_id == theatre_uuid,
            GateInstance.slot_id == slot_id
        ).first()
        
        if existing:
            logger.info(f"Gate already exists for slot {slot_id}")
            return existing
        
        # Calculate gate timing
        open_at = slot_start_at + timedelta(minutes=10)
        close_at = slot_start_at + timedelta(minutes=GATE_RESOLVE_MINUTE)
        resolve_at = close_at
        
        # Build options from config
        options = gate_config.get("options", [
            {"option_id": "opt_a", "label": "选项A"},
            {"option_id": "opt_b", "label": "选项B"}
        ])
        
        gate = GateInstance(
            theatre_id=theatre_uuid,
            slot_id=slot_id,
            gate_template_id=gate_config.get("template_id", "default"),
            type=gate_config.get("type", "Public"),
            status="SCHEDULED",
            title=gate_config.get("title", f"Gate for {slot_id}"),
            open_at=open_at,
            close_at=close_at,
            resolve_at=resolve_at,
            options_jsonb=options,
            base_prob_jsonb=gate_config.get("base_prob"),
            random_seed=secrets.randbelow(2**63)
        )
        
        self.db.add(gate)
        self.db.commit()
        
        logger.info(f"Created gate instance for slot {slot_id}")
        return gate
    
    def get_gate_instance(self, gate_instance_id: str) -> Optional[GateInstance]:
        """Get a gate instance by ID."""
        return self.db.query(GateInstance).filter(
            GateInstance.gate_instance_id == uuid.UUID(gate_instance_id)
        ).first()
    
    def get_gate_by_slot(self, slot_id: str) -> Optional[GateInstance]:
        """Get a gate instance by slot ID."""
        return self.db.query(GateInstance).filter(
            GateInstance.slot_id == slot_id
        ).first()
    
    def get_gate_lobby(self, gate_instance_id: str) -> Dict:
        """
        Get gate lobby information for clients.
        
        Returns options, countdown, current status (without exact totals).
        """
        gate = self.get_gate_instance(gate_instance_id)
        if not gate:
            return {"error": "Gate not found"}
        
        now = datetime.now(timezone.utc)
        
        # Calculate vote counts (bucketed for fairness)
        vote_counts = self._get_vote_counts_bucketed(gate.gate_instance_id)
        
        return {
            "gate_instance_id": str(gate.gate_instance_id),
            "slot_id": gate.slot_id,
            "type": gate.type,
            "status": gate.status,
            "title": gate.title,
            "options": gate.options_jsonb,
            "vote_distribution": vote_counts,  # Bucketed, not exact
            "open_at_ms": int(gate.open_at.replace(tzinfo=timezone.utc).timestamp() * 1000),
            "close_at_ms": int(gate.close_at.replace(tzinfo=timezone.utc).timestamp() * 1000),
            "resolve_at_ms": int(gate.resolve_at.replace(tzinfo=timezone.utc).timestamp() * 1000),
            "is_open": gate.status == "OPEN" and gate.open_at <= now.replace(tzinfo=None) <= gate.close_at,
            "winner_option_id": gate.winner_option_id,
            "explain_card": gate.explain_card_jsonb
        }
    
    def _get_vote_counts_bucketed(self, gate_instance_id: uuid.UUID) -> Dict[str, str]:
        """Get vote counts in buckets (few/some/many) for fairness."""
        votes = self.db.query(
            GateVote.option_id,
            func.count(GateVote.user_id).label("count")
        ).filter(
            GateVote.gate_instance_id == gate_instance_id
        ).group_by(GateVote.option_id).all()
        
        result = {}
        for option_id, count in votes:
            if count < 10:
                result[option_id] = "few"
            elif count < 50:
                result[option_id] = "some"
            elif count < 200:
                result[option_id] = "many"
            else:
                result[option_id] = "overwhelming"
        
        return result
    
    # =========================================================================
    # Voting
    # =========================================================================
    def submit_vote(
        self,
        gate_instance_id: str,
        user_id: str,
        request: VoteRequest
    ) -> VoteResult:
        """
        Submit or update a vote (idempotent).
        
        Users can change their vote during OPEN period.
        """
        gate = self.get_gate_instance(gate_instance_id)
        if not gate:
            return VoteResult(False, "Gate not found")
        
        # Check gate status
        if gate.status not in ["SCHEDULED", "OPEN"]:
            return VoteResult(False, f"Gate is {gate.status}, voting not allowed")
        
        # Auto-open gate if time has come
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if gate.status == "SCHEDULED" and now >= gate.open_at:
            gate.status = "OPEN"
            self.db.commit()
        
        if gate.status != "OPEN":
            return VoteResult(False, "Gate is not open yet")
        
        # Validate option
        valid_options = [opt["option_id"] for opt in gate.options_jsonb]
        if request.option_id not in valid_options:
            return VoteResult(False, f"Invalid option: {request.option_id}")
        
        gate_uuid = uuid.UUID(gate_instance_id)
        
        # Check existing vote
        existing = self.db.query(GateVote).filter(
            GateVote.gate_instance_id == gate_uuid,
            GateVote.user_id == user_id
        ).first()
        
        if existing:
            # Update vote
            existing.option_id = request.option_id
            existing.ring_level = request.ring_level
            existing.updated_at = datetime.utcnow()
            existing.idempotency_key = request.idempotency_key
            self.db.commit()
            logger.info(f"Updated vote for user {user_id} on gate {gate_instance_id}")
            return VoteResult(True, "Vote updated", str(gate_uuid))
        else:
            # Create new vote
            vote = GateVote(
                gate_instance_id=gate_uuid,
                user_id=user_id,
                option_id=request.option_id,
                ring_level=request.ring_level,
                idempotency_key=request.idempotency_key
            )
            self.db.add(vote)
            self.db.commit()
            logger.info(f"Created vote for user {user_id} on gate {gate_instance_id}")
            return VoteResult(True, "Vote submitted", str(gate_uuid))
    
    # =========================================================================
    # Staking
    # =========================================================================
    def submit_stake(
        self,
        gate_instance_id: str,
        user_id: str,
        request: StakeRequest
    ) -> StakeResult:
        """
        Submit or increase a stake (idempotent, can only increase).
        
        Requires sufficient wallet balance.
        """
        gate = self.get_gate_instance(gate_instance_id)
        if not gate:
            return StakeResult(False, "Gate not found")
        
        # Check gate type allows staking
        if gate.type == "Public":
            return StakeResult(False, "Public gates do not allow staking")
        
        # Check gate status
        if gate.status not in ["SCHEDULED", "OPEN"]:
            return StakeResult(False, f"Gate is {gate.status}, staking not allowed")
        
        # Auto-open gate if time has come
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if gate.status == "SCHEDULED" and now >= gate.open_at:
            gate.status = "OPEN"
            self.db.commit()
        
        if gate.status != "OPEN":
            return StakeResult(False, "Gate is not open yet")
        
        # Validate option
        valid_options = [opt["option_id"] for opt in gate.options_jsonb]
        if request.option_id not in valid_options:
            return StakeResult(False, f"Invalid option: {request.option_id}")
        
        # Check wallet balance
        balance = self._get_balance(user_id, request.currency)
        if balance < request.amount:
            return StakeResult(False, f"Insufficient balance: {balance} < {request.amount}")
        
        gate_uuid = uuid.UUID(gate_instance_id)
        
        # Check existing stake
        existing = self.db.query(GateStake).filter(
            GateStake.gate_instance_id == gate_uuid,
            GateStake.user_id == user_id,
            GateStake.currency == request.currency
        ).first()
        
        if existing:
            # Can only increase stake, not decrease or change option
            if existing.option_id != request.option_id:
                return StakeResult(False, "Cannot change option after staking")
            
            additional = request.amount
            new_total = existing.amount_locked + additional
            
            # Lock additional amount
            self._lock_funds(user_id, request.currency, additional, gate_instance_id)
            
            existing.amount_locked = new_total
            existing.updated_at = datetime.utcnow()
            existing.idempotency_key = request.idempotency_key
            self.db.commit()
            
            logger.info(f"Increased stake for user {user_id}: +{additional}, total={new_total}")
            return StakeResult(True, "Stake increased", new_total)
        else:
            # Create new stake
            self._lock_funds(user_id, request.currency, request.amount, gate_instance_id)
            
            stake = GateStake(
                gate_instance_id=gate_uuid,
                user_id=user_id,
                currency=request.currency,
                option_id=request.option_id,
                amount_locked=request.amount,
                ring_level=request.ring_level,
                idempotency_key=request.idempotency_key
            )
            self.db.add(stake)
            self.db.commit()
            
            logger.info(f"Created stake for user {user_id}: {request.amount} {request.currency}")
            return StakeResult(True, "Stake submitted", request.amount)
    
    # =========================================================================
    # Wallet Operations
    # =========================================================================
    def _get_balance(self, user_id: str, currency: str) -> Decimal:
        """Get user's wallet balance."""
        wallet = self.db.query(WalletBalance).filter(
            WalletBalance.user_id == user_id,
            WalletBalance.currency == currency
        ).first()
        
        return wallet.balance if wallet else Decimal("0")
    
    def _lock_funds(self, user_id: str, currency: str, amount: Decimal, ref_id: str):
        """Lock funds from wallet for staking."""
        # Deduct from balance
        wallet = self.db.query(WalletBalance).filter(
            WalletBalance.user_id == user_id,
            WalletBalance.currency == currency
        ).first()
        
        if wallet:
            wallet.balance -= amount
        else:
            # Create wallet with negative balance (shouldn't happen with proper checks)
            wallet = WalletBalance(user_id=user_id, currency=currency, balance=-amount)
            self.db.add(wallet)
        
        # Record in ledger
        ledger = WalletLedger(
            user_id=user_id,
            currency=currency,
            delta=-amount,
            reason="STAKE_LOCK",
            ref_type="gate",
            ref_id=ref_id
        )
        self.db.add(ledger)
    
    def _credit_funds(self, user_id: str, currency: str, amount: Decimal, reason: str, ref_id: str):
        """Credit funds to wallet (payout)."""
        wallet = self.db.query(WalletBalance).filter(
            WalletBalance.user_id == user_id,
            WalletBalance.currency == currency
        ).first()
        
        if wallet:
            wallet.balance += amount
        else:
            wallet = WalletBalance(user_id=user_id, currency=currency, balance=amount)
            self.db.add(wallet)
        
        ledger = WalletLedger(
            user_id=user_id,
            currency=currency,
            delta=amount,
            reason=reason,
            ref_type="gate",
            ref_id=ref_id
        )
        self.db.add(ledger)
    
    def grant_initial_balance(self, user_id: str, currency: str = "SHARD", amount: Decimal = Decimal("100")):
        """Grant initial balance to a new user (for testing/onboarding)."""
        wallet = self.db.query(WalletBalance).filter(
            WalletBalance.user_id == user_id,
            WalletBalance.currency == currency
        ).first()
        
        if not wallet:
            wallet = WalletBalance(user_id=user_id, currency=currency, balance=amount)
            self.db.add(wallet)
            
            ledger = WalletLedger(
                user_id=user_id,
                currency=currency,
                delta=amount,
                reason="INITIAL_GRANT",
                ref_type="system",
                ref_id="onboarding"
            )
            self.db.add(ledger)
            self.db.commit()
            logger.info(f"Granted {amount} {currency} to user {user_id}")
    
    # =========================================================================
    # Gate Resolution
    # =========================================================================
    def resolve_gate(self, gate_instance_id: str) -> ResolveResult:
        """
        Resolve a gate and determine the winner.
        
        This is the core settlement logic:
        1. Close the gate
        2. Count votes with weighting
        3. Determine winner
        4. Calculate payouts (parimutuel)
        5. Generate Explain Card
        6. Apply delta to WorldState
        """
        gate = self.get_gate_instance(gate_instance_id)
        if not gate:
            return ResolveResult(False, error="Gate not found")
        
        # CAS: Only CLOSED gates can be resolved
        if gate.status == "RESOLVED":
            return ResolveResult(True, gate.winner_option_id, gate.explain_card_jsonb)
        
        if gate.status not in ["OPEN", "CLOSED"]:
            return ResolveResult(False, error=f"Gate status is {gate.status}, cannot resolve")
        
        # Close the gate first
        if gate.status == "OPEN":
            gate.status = "CLOSED"
            self.db.commit()
        
        # Transition to RESOLVING
        gate.status = "RESOLVING"
        self.db.commit()
        
        gate_uuid = uuid.UUID(gate_instance_id)
        
        try:
            # 1. Count votes with weighting
            vote_weights = self._calculate_vote_weights(gate_uuid)
            
            # 2. Count stakes
            stake_weights = self._calculate_stake_weights(gate_uuid)
            
            # 3. Combine and determine winner
            combined_weights = {}
            for option_id in [opt["option_id"] for opt in gate.options_jsonb]:
                combined_weights[option_id] = (
                    vote_weights.get(option_id, 0) * 0.7 +  # 70% vote weight
                    stake_weights.get(option_id, 0) * 0.3   # 30% stake weight
                )
            
            # Winner is the option with highest combined weight
            if combined_weights:
                winner_option_id = max(combined_weights, key=combined_weights.get)
            else:
                # No votes/stakes, use random seed
                options = [opt["option_id"] for opt in gate.options_jsonb]
                winner_option_id = options[gate.random_seed % len(options)]
            
            # 4. Calculate and distribute payouts
            settlement_summary = self._settle_stakes(gate_uuid, winner_option_id)
            
            # 5. Generate Explain Card
            explain_card = self._generate_explain_card(
                gate=gate,
                winner_option_id=winner_option_id,
                vote_weights=vote_weights,
                stake_weights=stake_weights,
                settlement_summary=settlement_summary
            )
            
            # 6. Apply delta to WorldState
            self._apply_gate_outcome_to_world(gate, winner_option_id)
            
            # Update gate
            gate.winner_option_id = winner_option_id
            gate.explain_card_jsonb = explain_card
            gate.status = "RESOLVED"
            self.db.commit()
            
            logger.info(f"Gate {gate_instance_id} resolved: winner={winner_option_id}")
            return ResolveResult(True, winner_option_id, explain_card)
            
        except Exception as e:
            logger.error(f"Gate resolution failed: {e}")
            gate.status = "CLOSED"  # Rollback status
            self.db.commit()
            return ResolveResult(False, error=str(e))
    
    def _calculate_vote_weights(self, gate_instance_id: uuid.UUID) -> Dict[str, float]:
        """Calculate weighted vote counts."""
        votes = self.db.query(GateVote).filter(
            GateVote.gate_instance_id == gate_instance_id
        ).all()
        
        weights = {}
        for vote in votes:
            # Ring level bonus
            ring_bonus = {"A": 1.5, "B": 1.2, "C": 1.0}.get(vote.ring_level, 1.0)
            weight = 1.0 * ring_bonus
            
            weights[vote.option_id] = weights.get(vote.option_id, 0) + weight
        
        # Normalize
        total = sum(weights.values()) or 1
        return {k: v / total for k, v in weights.items()}
    
    def _calculate_stake_weights(self, gate_instance_id: uuid.UUID) -> Dict[str, float]:
        """Calculate weighted stake amounts (sqrt for fairness)."""
        stakes = self.db.query(GateStake).filter(
            GateStake.gate_instance_id == gate_instance_id
        ).all()
        
        weights = {}
        for stake in stakes:
            # Use sqrt for anti-whale
            weight = float(stake.amount_locked.sqrt()) if stake.amount_locked > 0 else 0
            weights[stake.option_id] = weights.get(stake.option_id, 0) + weight
        
        # Normalize
        total = sum(weights.values()) or 1
        return {k: v / total for k, v in weights.items()}
    
    def _settle_stakes(self, gate_instance_id: uuid.UUID, winner_option_id: str) -> Dict:
        """
        Settle stakes using parimutuel system.
        
        Returns summary of settlement.
        """
        stakes = self.db.query(GateStake).filter(
            GateStake.gate_instance_id == gate_instance_id
        ).all()
        
        if not stakes:
            return {"total_pool": 0, "winner_pool": 0, "fee_burned": 0}
        
        # Group by currency
        currency_pools = {}
        for stake in stakes:
            if stake.currency not in currency_pools:
                currency_pools[stake.currency] = {"total": Decimal("0"), "winner": Decimal("0"), "stakes": []}
            
            currency_pools[stake.currency]["total"] += stake.amount_locked
            currency_pools[stake.currency]["stakes"].append(stake)
            
            if stake.option_id == winner_option_id:
                currency_pools[stake.currency]["winner"] += stake.amount_locked
        
        total_fee_burned = Decimal("0")
        
        # Settle each currency
        for currency, pool in currency_pools.items():
            total = pool["total"]
            winner_total = pool["winner"]
            
            # Calculate fee
            fee = total * GATE_FEE_RATE
            distributable = total - fee
            total_fee_burned += fee
            
            for stake in pool["stakes"]:
                if stake.option_id == winner_option_id and winner_total > 0:
                    # Winner: get proportional share
                    payout = distributable * (stake.amount_locked / winner_total)
                    net_delta = payout - stake.amount_locked
                else:
                    # Loser: lose stake
                    payout = Decimal("0")
                    net_delta = -stake.amount_locked
                
                stake.amount_final = payout
                
                # Record settlement
                settlement = GateSettlement(
                    gate_instance_id=gate_instance_id,
                    user_id=stake.user_id,
                    currency=currency,
                    stake=stake.amount_locked,
                    payout=payout,
                    fee_burn=fee * (stake.amount_locked / total) if total > 0 else Decimal("0"),
                    net_delta=net_delta
                )
                self.db.add(settlement)
                
                # Credit payout to wallet
                if payout > 0:
                    self._credit_funds(
                        stake.user_id, currency, payout,
                        "STAKE_PAYOUT", str(gate_instance_id)
                    )
        
        return {
            "total_pool": float(sum(p["total"] for p in currency_pools.values())),
            "winner_pool": float(sum(p["winner"] for p in currency_pools.values())),
            "fee_burned": float(total_fee_burned)
        }
    
    def _generate_explain_card(
        self,
        gate: GateInstance,
        winner_option_id: str,
        vote_weights: Dict[str, float],
        stake_weights: Dict[str, float],
        settlement_summary: Dict
    ) -> Dict:
        """Generate the Explain Card for this gate resolution."""
        # Find winner option details
        winner_option = next(
            (opt for opt in gate.options_jsonb if opt["option_id"] == winner_option_id),
            {"option_id": winner_option_id, "label": "Unknown"}
        )
        
        return {
            "gate_instance_id": str(gate.gate_instance_id),
            "slot_id": gate.slot_id,
            "gate_type": gate.type,
            "title": gate.title,
            "winner": {
                "option_id": winner_option_id,
                "label": winner_option.get("label", ""),
                "vote_share": vote_weights.get(winner_option_id, 0),
                "stake_share": stake_weights.get(winner_option_id, 0)
            },
            "vote_distribution": {
                opt["option_id"]: {
                    "label": opt.get("label", ""),
                    "share": vote_weights.get(opt["option_id"], 0)
                }
                for opt in gate.options_jsonb
            },
            "settlement": settlement_summary,
            "narrative_impact": f"集体选择了「{winner_option.get('label', winner_option_id)}」，这将影响接下来的剧情走向。",
            "resolved_at": datetime.now(timezone.utc).isoformat()
        }
    
    def _apply_gate_outcome_to_world(self, gate: GateInstance, winner_option_id: str):
        """Apply the gate outcome to WorldState via Kernel."""
        kernel = KernelService(self.db)
        
        # Build delta based on gate outcome
        # In production, this would be driven by GateTemplate
        ops = []
        
        # Example: winning option affects world tension
        if winner_option_id == "opt_a":
            ops.append({"op": "world_var_add", "var_id": "tension", "delta": 0.05})
        elif winner_option_id == "opt_b":
            ops.append({"op": "world_var_add", "var_id": "tension", "delta": -0.03})
        elif winner_option_id == "opt_c":
            ops.append({"op": "world_var_add", "var_id": "mystery", "delta": 0.08})
        
        if ops:
            delta_request = ApplyDeltaRequest(
                delta_id=f"gate_{gate.gate_instance_id}_outcome",
                expected_version=-1,  # Skip version check for gate outcomes
                source={"gate_instance_id": str(gate.gate_instance_id)},
                ops=ops
            )
            
            result = kernel.apply_delta(str(gate.theatre_id), delta_request)
            if not result.applied:
                logger.warning(f"Failed to apply gate outcome to world: {result.error}")
    
    # =========================================================================
    # Auto-management
    # =========================================================================
    def check_and_update_gate_status(self, gate_instance_id: str) -> str:
        """Check and update gate status based on current time."""
        gate = self.get_gate_instance(gate_instance_id)
        if not gate:
            return "NOT_FOUND"
        
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        if gate.status == "SCHEDULED" and now >= gate.open_at:
            gate.status = "OPEN"
            self.db.commit()
            return "OPEN"
        
        if gate.status == "OPEN" and now >= gate.close_at:
            gate.status = "CLOSED"
            self.db.commit()
            # Auto-resolve
            self.resolve_gate(gate_instance_id)
            return "RESOLVED"
        
        return gate.status
    
    def get_pending_gates_to_resolve(self) -> List[GateInstance]:
        """Get gates that need to be resolved."""
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        
        return self.db.query(GateInstance).filter(
            GateInstance.status.in_(["OPEN", "CLOSED"]),
            GateInstance.resolve_at <= now
        ).all()
