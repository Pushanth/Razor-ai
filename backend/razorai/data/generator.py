import random
import uuid
import hashlib
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import numpy as np

from razorai.data.models import (
    Customer, Merchant, Device, Settlement,
    Transaction, PaymentMethod, TransactionStatus,
    FailureReason, RiskTier
)


INDIAN_CITIES = [
    "Mumbai, MH", "Bengaluru, KA", "New Delhi, DL", "Hyderabad, TS",
    "Pune, MH", "Chennai, TN", "Kolkata, WB", "Ahmedabad, GJ",
    "Jaipur, RJ", "Kochi, KL", "Chandigarh, CH", "Indore, MP"
]

MERCHANT_CATEGORIES = [
    "E-Commerce", "SaaS & Cloud", "EdTech", "Gaming & Entertainment",
    "Quick Commerce & Food", "Travel & Hospitality", "Financial Services", "Healthcare"
]

FIRST_NAMES = [
    "Aarav", "Aditi", "Rohan", "Priya", "Vikram", "Neha", "Rahul", "Ananya",
    "Amit", "Pooja", "Arjun", "Sneha", "Karan", "Divya", "Siddharth", "Meera",
    "Varun", "Rhea", "Nikhil", "Ishita", "Gaurav", "Tanvi", "Abhishek", "Kavya"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Mehta", "Iyer", "Nair", "Reddy", "Rao",
    "Gupta", "Singh", "Joshi", "Kulkarni", "Deshmukh", "Chopra", "Banerjee", "Bhat"
]

BANKS = ["HDFC", "SBI", "ICICI", "AXIS", "KOTAK", "YES_BANK", "INDUSIND"]


class SyntheticDataGenerator:
    """
    High-fidelity synthetic dataset generator creating realistic entities,
    temporal sequences, multi-layer fraud rings, bank outage spikes, and settlement anomalies.
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        random.seed(seed)
        np.random.seed(seed)

    def generate_customers(self, count: int = 1500) -> List[Customer]:
        customers = []
        for i in range(count):
            c_id = f"cust_{i+1:06d}"
            fname = random.choice(FIRST_NAMES)
            lname = random.choice(LAST_NAMES)
            name = f"{fname} {lname}"
            email = f"{fname.lower()}.{lname.lower()}{random.randint(10, 999)}@example.com"
            phone = f"+919{random.randint(100000000, 999999999)}"
            
            # Risk tier distribution: 90% LOW, 7% MEDIUM, 2.5% HIGH, 0.5% CRITICAL
            risk_rand = random.random()
            if risk_rand < 0.90:
                risk_tier = RiskTier.LOW
            elif risk_rand < 0.97:
                risk_tier = RiskTier.MEDIUM
            elif risk_rand < 0.995:
                risk_tier = RiskTier.HIGH
            else:
                risk_tier = RiskTier.CRITICAL

            created_at = datetime.utcnow() - timedelta(days=random.randint(30, 730))
            customers.append(Customer(
                id=c_id,
                name=name,
                email=email,
                phone=phone,
                created_at=created_at,
                risk_tier=risk_tier,
                total_gmv=0.0,
                tx_count=0,
                failure_count=0,
                linked_devices=[],
                linked_cards=[]
            ))
        return customers

    def generate_merchants(self, count: int = 120) -> List[Merchant]:
        merchants = []
        names = [
            "QuickKart India", "Apex Cloud Solutions", "EduPro Global", "VibeGaming Studio",
            "SwyftGroceries", "FlyHigh Travels", "BharatPay Mart", "Zenith Health",
            "TrendPulse Fashion", "UrbanStay Hotels", "Nova Electronics", "FinFlow Payments"
        ]
        
        for i in range(count):
            m_id = f"merch_{i+1:04d}"
            base_name = names[i % len(names)]
            name = f"{base_name} {i+1}" if i >= len(names) else base_name
            cat = random.choice(MERCHANT_CATEGORIES)
            monthly_gmv = round(random.uniform(500_000, 50_000_000), 2)
            success_rate = round(random.uniform(0.88, 0.96), 4)
            refund_rate = round(random.uniform(0.01, 0.05), 4)
            dispute_rate = round(random.uniform(0.0005, 0.008), 4)

            merchants.append(Merchant(
                id=m_id,
                name=name,
                category=cat,
                monthly_gmv=monthly_gmv,
                success_rate=success_rate,
                refund_rate=refund_rate,
                dispute_rate=dispute_rate,
                risk_profile=RiskTier.LOW if dispute_rate < 0.003 else RiskTier.MEDIUM,
                preferred_recovery_rail=PaymentMethod.UPI,
                webhook_url=f"https://api.{name.lower().replace(' ', '')}.com/webhooks"
            ))
        return merchants

    def generate_devices(self, count: int = 2500) -> List[Device]:
        devices = []
        os_list = ["Android 14", "Android 13", "iOS 17.4", "iOS 16.5", "Windows 11", "macOS Sonoma"]
        for i in range(count):
            d_id = f"dev_{uuid.uuid4().hex[:12]}"
            dev_type = "mobile" if "Android" in os_list[i % len(os_list)] or "iOS" in os_list[i % len(os_list)] else "desktop"
            os_name = random.choice(os_list)
            ip = f"{random.randint(10, 220)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
            
            # 1.5% fraud flagged devices
            fraud_flag = (random.random() < 0.015)
            devices.append(Device(
                id=d_id,
                device_type=dev_type,
                os=os_name,
                ip_addresses=[ip],
                associated_customers=[],
                fraud_flag=fraud_flag
            ))
        return devices

    def generate_transactions(
        self,
        customers: List[Customer],
        merchants: List[Merchant],
        devices: List[Device],
        count: int = 15000,
        inject_fraud_syndicate: bool = True,
        inject_bank_outage: bool = True
    ) -> List[Transaction]:
        transactions = []
        now = datetime.utcnow()

        # Build device & card associations
        for c in customers:
            assigned_dev = random.choice(devices)
            assigned_dev.associated_customers.append(c.id)
            c.linked_devices.append(assigned_dev.id)
            card_fp = f"card_{hashlib.md5(c.id.encode()).hexdigest()[:10]}"
            c.linked_cards.append(card_fp)

        # 1. Inject Fraud Syndicate (Coordinated ring sharing 1 device across 15 customers)
        syndicate_customers = customers[:15] if inject_fraud_syndicate else []
        syndicate_device = devices[0] if inject_fraud_syndicate else None
        if syndicate_device:
            syndicate_device.fraud_flag = True
            for sc in syndicate_customers:
                if syndicate_device.id not in sc.linked_devices:
                    sc.linked_devices.append(syndicate_device.id)
                sc.risk_tier = RiskTier.CRITICAL

        # 2. Bank Outage Target Rail
        outage_bank = "HDFC"
        outage_start_min = 120  # 2 hours ago
        outage_end_min = 60    # 1 hour ago

        for i in range(count):
            tx_id = f"pay_{uuid.uuid4().hex[:14]}"
            
            # Temporal dispersion over last 24 hours
            minutes_ago = random.expovariate(1.0 / 240) # exponential clustering
            minutes_ago = min(minutes_ago, 24 * 60)
            tx_time = now - timedelta(minutes=minutes_ago)

            # Is this part of the syndicate?
            is_syndicate_tx = (inject_fraud_syndicate and random.random() < 0.04 and len(syndicate_customers) > 0)
            if is_syndicate_tx:
                customer = random.choice(syndicate_customers)
                device = syndicate_device
                merchant = merchants[0] # concentrated on high-ticket merchant
                amount = round(random.uniform(15_000, 95_000), 2)
                method = PaymentMethod.CARD
                card_fp = f"card_stolen_{random.randint(1, 3)}"
                location = "Unknown / Proxy Exit"
                ip = f"185.220.{random.randint(100, 250)}.{random.randint(1, 254)}"
            else:
                customer = random.choice(customers)
                merchant = random.choice(merchants)
                device = random.choice(devices)
                
                # Payment method distribution (65% UPI, 20% Card, 10% Netbanking, 5% EMI/Wallet)
                pm_rand = random.random()
                if pm_rand < 0.65:
                    method = PaymentMethod.UPI
                    amount = round(random.expovariate(1.0 / 1200) + 50, 2)
                elif pm_rand < 0.85:
                    method = PaymentMethod.CARD
                    amount = round(random.expovariate(1.0 / 3500) + 200, 2)
                elif pm_rand < 0.95:
                    method = PaymentMethod.NETBANKING
                    amount = round(random.expovariate(1.0 / 5000) + 500, 2)
                else:
                    method = random.choice([PaymentMethod.WALLET, PaymentMethod.EMI])
                    amount = round(random.uniform(1000, 45000), 2)

                amount = min(amount, 250_000.0) # cap
                card_fp = customer.linked_cards[0] if customer.linked_cards else f"card_{uuid.uuid4().hex[:8]}"
                location = random.choice(INDIAN_CITIES)
                ip = device.ip_addresses[0] if device.ip_addresses else "103.21.244.2"

            # Determine transaction outcome & failure reasoning
            is_outage_window = (outage_end_min <= minutes_ago <= outage_start_min)
            is_outage_affected = (inject_bank_outage and is_outage_window and method == PaymentMethod.UPI and random.random() < 0.70)

            if is_syndicate_tx:
                # Syndicate transactions are often blocked or fail auth
                status = TransactionStatus.FAILED
                failure_reason = FailureReason.FRAUD_BLOCKED if random.random() < 0.6 else FailureReason.AUTH_FAILED
                risk_score = round(random.uniform(0.85, 0.99), 3)
                risk_tier = RiskTier.CRITICAL
            elif is_outage_affected:
                status = TransactionStatus.FAILED
                failure_reason = FailureReason.BANK_TIMEOUT
                risk_score = round(random.uniform(0.05, 0.20), 3)
                risk_tier = RiskTier.LOW
            else:
                # Normal merchant success baseline
                if random.random() < merchant.success_rate:
                    status = TransactionStatus.SUCCESS
                    failure_reason = FailureReason.NONE
                    risk_score = round(random.uniform(0.01, 0.25), 3)
                    risk_tier = RiskTier.LOW
                else:
                    status = TransactionStatus.FAILED
                    fail_choices = [
                        FailureReason.INSUFFICIENT_FUNDS,
                        FailureReason.BANK_TIMEOUT,
                        FailureReason.AUTH_FAILED,
                        FailureReason.CARD_EXPIRED,
                        FailureReason.LIMIT_EXCEEDED
                    ]
                    failure_reason = random.choice(fail_choices)
                    risk_score = round(random.uniform(0.10, 0.65), 3)
                    risk_tier = RiskTier.MEDIUM if risk_score > 0.4 else RiskTier.LOW

            tx = Transaction(
                id=tx_id,
                customer_id=customer.id,
                merchant_id=merchant.id,
                amount=amount,
                currency="INR",
                payment_method=method,
                status=status,
                failure_reason=failure_reason,
                device_id=device.id,
                card_fingerprint=card_fp,
                ip_address=ip,
                location=location,
                timestamp=tx_time,
                risk_score=risk_score,
                risk_tier=risk_tier,
                latency_ms=round(random.uniform(28.0, 140.0), 1),
                metadata={"bank": random.choice(BANKS), "is_syndicate": is_syndicate_tx}
            )
            transactions.append(tx)

            # Update customer counters
            customer.tx_count += 1
            if status == TransactionStatus.SUCCESS:
                customer.total_gmv += amount
            else:
                customer.failure_count += 1

        # Sort chronologically
        transactions.sort(key=lambda x: x.timestamp)
        return transactions

    def generate_settlements(self, merchants: List[Merchant], count_days: int = 7) -> List[Settlement]:
        settlements = []
        now = datetime.utcnow().date()

        for m in merchants[:30]:
            for d in range(count_days):
                settle_date = (now - timedelta(days=d+1)).isoformat()
                s_id = f"set_{m.id}_{settle_date.replace('-', '')}"
                
                daily_volume = round(m.monthly_gmv / 30.0 * random.uniform(0.8, 1.25), 2)
                refund_deduction = round(daily_volume * m.refund_rate * random.uniform(0.9, 1.1), 2)
                fee_deduction = round(daily_volume * 0.018, 2) # ~1.8% MDR fee
                chargeback_deduction = round(daily_volume * m.dispute_rate, 2)
                reserve_holdback = round(daily_volume * 0.01, 2) # 1% rolling reserve

                expected_payout = round(
                    daily_volume - refund_deduction - fee_deduction - chargeback_deduction - reserve_holdback, 2
                )

                # Inject settlement discrepancy on 5% of records for autonomous finance agent
                has_discrepancy = (random.random() < 0.08)
                if has_discrepancy:
                    # e.g., bank transferred less due to unrecorded fee/chargeback or missing refund sync
                    discrepancy_variance = round(random.uniform(15_000, 95_000), 2)
                    actual_payout = round(expected_payout - discrepancy_variance, 2)
                    discrepancy_amount = discrepancy_variance
                    status = "DISCREPANCY"
                else:
                    actual_payout = expected_payout
                    discrepancy_amount = 0.0
                    status = "SETTLED"

                settlements.append(Settlement(
                    id=s_id,
                    merchant_id=m.id,
                    date=settle_date,
                    gross_volume=daily_volume,
                    refund_deduction=refund_deduction,
                    fee_deduction=fee_deduction,
                    chargeback_deduction=chargeback_deduction,
                    reserve_holdback=reserve_holdback,
                    expected_payout=expected_payout,
                    actual_payout=actual_payout,
                    discrepancy_amount=discrepancy_amount,
                    status=status
                ))
        return settlements
