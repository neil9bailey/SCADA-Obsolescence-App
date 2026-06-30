from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Asset, AuditEvent, Programme
from app.services.risk import apply_assessment


def seed_demo_data(db: Session) -> bool:
    if int(db.scalar(select(func.count()).select_from(Asset)) or 0) > 0:
        return False

    programmes = [
        Programme(
            package_code="OBP-001",
            title="Central SCADA Core Renewal",
            description="Replace the unsupported supervisory servers, operator clients and core communications services.",
            owner="Control Systems Engineering",
            sponsor="Director of Operations",
            status="design",
            target_wave="Wave 1",
            budget_estimate=Decimal("1250000"),
            contingency_percent=25,
            target_start=date(2026, 9, 1),
            target_finish=date(2027, 5, 31),
            outage_window="Spring 2027 planned shutdown",
            target_platform="Resilient virtual SCADA platform with managed OT boundary services",
            dependencies="OT virtualisation cluster; identity integration; telecoms resilience",
        ),
        Programme(
            package_code="OBP-002",
            title="North Pumping PLC and Telemetry Upgrade",
            description="Migrate constrained controller families and radio telemetry gateways by pumping station cluster.",
            owner="North Region Engineering",
            sponsor="Regional Operations Manager",
            status="business_case",
            target_wave="Wave 1",
            budget_estimate=Decimal("860000"),
            contingency_percent=30,
            target_start=date(2026, 11, 1),
            target_finish=date(2027, 10, 31),
            outage_window="Rolling station outages, maximum four hours each",
            target_platform="Standard PLC family and secure telemetry edge gateway",
            dependencies="Radio survey; panel modifications; spares strategy",
        ),
        Programme(
            package_code="OBP-003",
            title="Historian and Reporting Consolidation",
            description="Consolidate isolated historians and reporting databases onto a supported service pattern.",
            owner="Operational Data Services",
            sponsor="Chief Digital Officer",
            status="discovery",
            target_wave="Wave 2",
            budget_estimate=Decimal("440000"),
            contingency_percent=20,
            target_start=date(2027, 1, 15),
            target_finish=date(2027, 9, 30),
            target_platform="Central historian service with buffered OT data collectors",
            dependencies="Data-retention policy; interface rationalisation",
        ),
        Programme(
            package_code="OBP-004",
            title="Legacy Remote Access Containment",
            description="Remove unmanaged dial-in and direct vendor access while replacement projects mature.",
            owner="OT Cyber Security",
            sponsor="CISO",
            status="delivery",
            target_wave="Wave 0",
            budget_estimate=Decimal("185000"),
            contingency_percent=15,
            target_start=date(2026, 6, 1),
            target_finish=date(2026, 10, 31),
            target_platform="Brokered, monitored and time-bound vendor access",
            dependencies="Firewall changes; supplier onboarding; support procedures",
        ),
        Programme(
            package_code="OBP-005",
            title="South Site HMI and Alarm Refresh",
            description="Renew operator workstations and rationalise alarm presentation without changing control intent.",
            owner="South Site Automation",
            sponsor="South Site Manager",
            status="options",
            target_wave="Wave 2",
            budget_estimate=Decimal("610000"),
            contingency_percent=25,
            target_start=date(2027, 4, 1),
            target_finish=date(2028, 1, 31),
            outage_window="Autumn 2027 maintenance campaign",
            target_platform="Supported HMI clients with standard alarm philosophy",
            dependencies="Alarm rationalisation; operator training; SCADA core renewal",
        ),
    ]
    db.add_all(programmes)
    db.flush()
    programme_by_code = {programme.package_code: programme.id for programme in programmes}

    rows = [
        dict(asset_code="CTR-SCADA-001", system_name="Central SCADA primary server", site="Central Works", process_area="Control room", asset_type="SCADA Server", manufacturer="Orion Industrial", model="ControlSphere 7", software_version="7.4", os_version="Server OS 2012 generation", support_status="end_of_support", support_end_date=date(2023, 10, 10), business_criticality=5, safety_impact=4, production_impact=5, cyber_exposure=5, failure_likelihood=4, spares_risk=3, recoverability_risk=5, dependency_complexity=5, evidence_confidence="A", delivery_readiness=4, treatment="replace", owner="Control Systems Engineering", programme_id=programme_by_code["OBP-001"], notes="Failover has not been fully exercised in the last 12 months."),
        dict(asset_code="CTR-SCADA-002", system_name="Central SCADA standby server", site="Central Works", process_area="Control room", asset_type="SCADA Server", manufacturer="Orion Industrial", model="ControlSphere 7", software_version="7.4", os_version="Server OS 2012 generation", support_status="end_of_support", support_end_date=date(2023, 10, 10), business_criticality=5, safety_impact=4, production_impact=5, cyber_exposure=4, failure_likelihood=4, spares_risk=3, recoverability_risk=4, dependency_complexity=5, evidence_confidence="A", delivery_readiness=4, treatment="replace", owner="Control Systems Engineering", programme_id=programme_by_code["OBP-001"]),
        dict(asset_code="CTR-EWS-001", system_name="Primary engineering workstation", site="Central Works", process_area="Engineering office", asset_type="Engineering Workstation", manufacturer="Blueforge Systems", model="RuggedDesk E5", software_version="Engineering Suite 5.2", os_version="Desktop OS 7 generation", support_status="end_of_support", support_end_date=date(2020, 1, 14), business_criticality=5, safety_impact=5, production_impact=5, cyber_exposure=5, failure_likelihood=4, spares_risk=4, recoverability_risk=5, dependency_complexity=4, evidence_confidence="B", delivery_readiness=2, treatment="contain", owner="Control Systems Engineering", programme_id=programme_by_code["OBP-004"], notes="Only workstation holding one legacy controller programming package."),
        dict(asset_code="CTR-HMI-001", system_name="Control room operator station A", site="Central Works", process_area="Control room", asset_type="Operator Workstation", manufacturer="Blueforge Systems", model="PanelDesk 24", software_version="HMI Runtime 7.4", os_version="Desktop OS 10 generation", support_status="limited", support_end_date=date(2027, 4, 30), business_criticality=4, safety_impact=4, production_impact=5, cyber_exposure=3, failure_likelihood=3, spares_risk=3, recoverability_risk=3, dependency_complexity=4, evidence_confidence="A", delivery_readiness=4, treatment="upgrade", owner="Operations Technology", programme_id=programme_by_code["OBP-001"]),
        dict(asset_code="CTR-COMMS-001", system_name="Legacy protocol gateway", site="Central Works", process_area="OT communications room", asset_type="Protocol Gateway", manufacturer="Redwood Controls", model="BridgeMaster 200", firmware_version="2.9.1", support_status="unknown", business_criticality=5, safety_impact=4, production_impact=5, cyber_exposure=5, failure_likelihood=4, spares_risk=5, recoverability_risk=5, dependency_complexity=5, evidence_confidence="D", delivery_readiness=1, treatment="assess", owner=None, programme_id=programme_by_code["OBP-001"], notes="Dependency map incomplete; gateway aggregates seven remote sites."),
        dict(asset_code="CTR-HIST-001", system_name="Central process historian", site="Central Works", process_area="Data centre", asset_type="Historian", manufacturer="Meridian Data", model="Chronicle Enterprise", software_version="11.1", os_version="Server OS 2019 generation", support_status="supported", support_end_date=date(2029, 12, 31), business_criticality=4, safety_impact=2, production_impact=4, cyber_exposure=3, failure_likelihood=2, spares_risk=2, recoverability_risk=3, dependency_complexity=5, evidence_confidence="A", delivery_readiness=3, treatment="retain", owner="Operational Data Services", programme_id=programme_by_code["OBP-003"]),
        dict(asset_code="CTR-RAS-001", system_name="Vendor remote support appliance", site="Central Works", process_area="OT DMZ", asset_type="Remote Access", manufacturer="LegacyLink", model="ServiceGate 100", firmware_version="1.8", support_status="end_of_support", support_end_date=date(2022, 6, 30), business_criticality=4, safety_impact=4, production_impact=4, cyber_exposure=5, failure_likelihood=3, spares_risk=4, recoverability_risk=4, dependency_complexity=3, evidence_confidence="A", delivery_readiness=5, treatment="decommission", owner="OT Cyber Security", programme_id=programme_by_code["OBP-004"]),
        dict(asset_code="NTH-PLC-001", system_name="North inlet pumping PLC", site="North Pumping", process_area="Inlet station", asset_type="PLC", manufacturer="Aster Automation", model="AX-400", firmware_version="4.12", support_status="limited", support_end_date=date(2027, 12, 31), business_criticality=5, safety_impact=5, production_impact=5, cyber_exposure=3, failure_likelihood=4, spares_risk=5, recoverability_risk=4, dependency_complexity=4, evidence_confidence="A", delivery_readiness=3, treatment="replace", owner="North Region Engineering", programme_id=programme_by_code["OBP-002"]),
        dict(asset_code="NTH-PLC-002", system_name="North transfer pumping PLC", site="North Pumping", process_area="Transfer station", asset_type="PLC", manufacturer="Aster Automation", model="AX-400", firmware_version="4.10", support_status="limited", support_end_date=date(2027, 12, 31), business_criticality=4, safety_impact=4, production_impact=5, cyber_exposure=3, failure_likelihood=3, spares_risk=5, recoverability_risk=4, dependency_complexity=3, evidence_confidence="A", delivery_readiness=3, treatment="replace", owner="North Region Engineering", programme_id=programme_by_code["OBP-002"]),
        dict(asset_code="NTH-RTU-001", system_name="Reservoir telemetry RTU", site="North Pumping", process_area="Remote reservoir", asset_type="RTU", manufacturer="Redwood Controls", model="FieldNode 8", firmware_version="3.3", support_status="end_of_support", support_end_date=date(2024, 3, 31), business_criticality=4, safety_impact=4, production_impact=4, cyber_exposure=4, failure_likelihood=4, spares_risk=5, recoverability_risk=5, dependency_complexity=3, evidence_confidence="B", delivery_readiness=2, treatment="contain", owner="North Region Engineering", programme_id=programme_by_code["OBP-002"]),
        dict(asset_code="NTH-RAD-001", system_name="North telemetry radio master", site="North Pumping", process_area="Radio room", asset_type="Communications", manufacturer="Cobalt Wireless", model="WaveLink M6", firmware_version="6.0.2", support_status="unknown", business_criticality=4, safety_impact=3, production_impact=5, cyber_exposure=4, failure_likelihood=3, spares_risk=4, recoverability_risk=4, dependency_complexity=5, evidence_confidence="D", delivery_readiness=1, treatment="assess", owner="Telecoms Engineering", programme_id=programme_by_code["OBP-002"]),
        dict(asset_code="NTH-HMI-001", system_name="North local operator panel", site="North Pumping", process_area="Main panel", asset_type="HMI Panel", manufacturer="Aster Automation", model="ViewPanel 12", firmware_version="5.6", support_status="supported", support_end_date=date(2030, 6, 30), business_criticality=3, safety_impact=3, production_impact=4, cyber_exposure=2, failure_likelihood=2, spares_risk=2, recoverability_risk=3, dependency_complexity=2, evidence_confidence="A", delivery_readiness=3, treatment="retain", owner="North Region Engineering", programme_id=programme_by_code["OBP-002"]),
        dict(asset_code="STH-HMI-001", system_name="South control room station A", site="South Treatment", process_area="Control room", asset_type="Operator Workstation", manufacturer="Blueforge Systems", model="PanelDesk 22", software_version="HMI Runtime 6.8", os_version="Desktop OS 8 generation", support_status="end_of_support", support_end_date=date(2023, 1, 10), business_criticality=4, safety_impact=4, production_impact=5, cyber_exposure=4, failure_likelihood=4, spares_risk=4, recoverability_risk=4, dependency_complexity=4, evidence_confidence="B", delivery_readiness=3, treatment="replace", owner="South Site Automation", programme_id=programme_by_code["OBP-005"]),
        dict(asset_code="STH-HMI-002", system_name="South control room station B", site="South Treatment", process_area="Control room", asset_type="Operator Workstation", manufacturer="Blueforge Systems", model="PanelDesk 22", software_version="HMI Runtime 6.8", os_version="Desktop OS 8 generation", support_status="end_of_support", support_end_date=date(2023, 1, 10), business_criticality=4, safety_impact=4, production_impact=5, cyber_exposure=4, failure_likelihood=4, spares_risk=4, recoverability_risk=4, dependency_complexity=4, evidence_confidence="B", delivery_readiness=3, treatment="replace", owner="South Site Automation", programme_id=programme_by_code["OBP-005"]),
        dict(asset_code="STH-ALM-001", system_name="Alarm notification service", site="South Treatment", process_area="Control room", asset_type="Alarm Server", manufacturer="SignalWorks", model="NotifyPro 4", software_version="4.1", os_version="Server OS 2012 generation", support_status="end_of_support", support_end_date=date(2024, 12, 31), business_criticality=4, safety_impact=5, production_impact=4, cyber_exposure=4, failure_likelihood=3, spares_risk=3, recoverability_risk=4, dependency_complexity=4, evidence_confidence="A", delivery_readiness=2, treatment="contain", owner="South Site Automation", programme_id=programme_by_code["OBP-005"]),
        dict(asset_code="STH-HIST-001", system_name="South local historian", site="South Treatment", process_area="Server room", asset_type="Historian", manufacturer="Meridian Data", model="Chronicle Compact", software_version="8.9", os_version="Server OS 2012 generation", support_status="limited", support_end_date=date(2027, 3, 31), business_criticality=3, safety_impact=2, production_impact=4, cyber_exposure=3, failure_likelihood=3, spares_risk=3, recoverability_risk=4, dependency_complexity=4, evidence_confidence="B", delivery_readiness=2, treatment="upgrade", owner="Operational Data Services", programme_id=programme_by_code["OBP-003"]),
        dict(asset_code="EST-SW-001", system_name="East OT aggregation switch", site="East Remote", process_area="Communications cabinet", asset_type="Network Switch", manufacturer="Cobalt Networks", model="IronSwitch 24", firmware_version="9.2", support_status="limited", support_end_date=date(2028, 2, 28), business_criticality=4, safety_impact=3, production_impact=4, cyber_exposure=3, failure_likelihood=2, spares_risk=3, recoverability_risk=3, dependency_complexity=5, evidence_confidence="A", delivery_readiness=2, treatment="retain", owner="OT Network Engineering", programme_id=None),
        dict(asset_code="EST-RTU-001", system_name="East remote telemetry RTU", site="East Remote", process_area="Remote compound", asset_type="RTU", manufacturer="Redwood Controls", model="FieldNode 10", firmware_version="4.2", support_status="supported", support_end_date=date(2031, 12, 31), business_criticality=3, safety_impact=3, production_impact=3, cyber_exposure=3, failure_likelihood=2, spares_risk=2, recoverability_risk=3, dependency_complexity=3, evidence_confidence="A", delivery_readiness=2, treatment="retain", owner="East Region Engineering", programme_id=None),
        dict(asset_code="WST-UPS-001", system_name="West control UPS monitoring gateway", site="West Storage", process_area="Electrical room", asset_type="Protocol Gateway", manufacturer="Voltview", model="PowerBridge 3", firmware_version="1.2", support_status="unknown", business_criticality=2, safety_impact=2, production_impact=3, cyber_exposure=3, failure_likelihood=3, spares_risk=4, recoverability_risk=3, dependency_complexity=2, evidence_confidence="D", delivery_readiness=1, treatment="assess", owner=None, programme_id=None),
        dict(asset_code="WST-PLC-001", system_name="West storage transfer PLC", site="West Storage", process_area="Transfer pumps", asset_type="PLC", manufacturer="Aster Automation", model="AX-800", firmware_version="8.6", support_status="supported", support_end_date=date(2032, 12, 31), business_criticality=4, safety_impact=3, production_impact=4, cyber_exposure=2, failure_likelihood=2, spares_risk=2, recoverability_risk=2, dependency_complexity=3, evidence_confidence="A", delivery_readiness=2, treatment="retain", owner="West Region Engineering", programme_id=None),
    ]

    assets = []
    for row in rows:
        asset = Asset(**row)
        apply_assessment(asset)
        assets.append(asset)
    db.add_all(assets)
    db.add(
        AuditEvent(
            entity_type="system",
            entity_id=None,
            action="seed",
            summary=f"Loaded fictional demonstration portfolio with {len(assets)} assets and {len(programmes)} programmes",
            actor="demo seed",
        )
    )
    db.commit()
    return True
