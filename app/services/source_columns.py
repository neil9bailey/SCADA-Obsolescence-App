from __future__ import annotations

from app.schemas_live import SourceColumnDefinition

SOURCE_COLUMN_GROUPS: list[tuple[str, str, str, str, bool, bool]] = [
    ("Last Obsolescence Check or Update", "Lifecycle", "date", "Last Obsolescence Check or Update", True, False),
    ("Component Part", "Identity", "text", "Component Part", True, True),
    ("Component", "Identity", "text", "Component", True, True),
    ("Component Description", "Identity", "textarea", "Component Description", True, False),
    ("Manufacturer", "Vendor", "text", "Manufacturer", True, False),
    ("Supplier", "Vendor", "text", "Supplier", True, False),
    ("Responsible Team", "Ownership", "text", "Responsible Team", True, False),
    ("Area", "Ownership", "text", "Area", True, True),
    ("Hardware/Software", "Technology", "select", "Hardware/Software", True, False),
    ("Functional / Non-Functional", "Technology", "select", "Functional / Non-Functional", False, False),
    ("Obsolete (Y/N)", "Lifecycle", "select", "Obsolete (Y/N)", True, False),
    ("Obsolete Date", "Lifecycle", "date", "Obsolete Date", False, False),
    ("Last Buy", "Lifecycle", "date", "Last Buy", False, False),
    ("End of Support", "Lifecycle", "date", "End of Support", True, False),
    ("Cost Hit (EOS - 1 Year)", "Lifecycle", "date", "Cost Hit (EOS - 1 Year)", False, False),
    ("Obsolescence Management Strategy", "Lifecycle", "textarea", "Obsolescence Management Strategy", False, False),
    ("Status", "Lifecycle", "text", "Status", True, False),
    ("Qty in Field", "Spares", "number", "Qty in Field", True, False),
    ("NR Spares Oty (Battle Boxes)", "Spares", "number", "NR Spares Qty", False, False),
    ("Telent Spares Qty", "Spares", "number", "Telent Spares Qty", False, False),
    ("Recommend No of Spares", "Spares", "number", "Recommended Spares", False, False),
    ("Future Installation Qty", "Spares", "number", "Future Installation Qty", False, False),
    ("Spares Strategy", "Spares", "textarea", "Spares Strategy", False, False),
    ("Unit Cost (est)", "Cost", "currency", "Unit Cost (est)", False, False),
    ("Cost (of Total Devices in Field)", "Cost", "currency", "Cost of Total Devices in Field", False, False),
    ("Estimated Procurement Lead Time (Days)", "Cost", "number", "Estimated Procurement Lead Time (Days)", False, False),
    ("Estimated Labour Cost", "Cost", "currency", "Estimated Labour Cost", False, False),
    ("Total Estimated Cost (Component + Labour)", "Cost", "currency", "Total Estimated Cost", False, False),
    ("PA Subsystem Cert Reference", "Certificates", "text", "PA Subsystem Cert Reference", False, False),
    ("PA (Product Specific) Certificate Reference", "Certificates", "text", "PA Product Certificate Reference", False, False),
    ("Full upgrade or ad-hoc replacement?", "Treatment", "text", "Upgrade or Replacement Type", False, False),
    ("System Criticality", "Risk", "number", "System Criticality", True, False),
    ("Obsolescence Criticality", "Risk", "number", "Obsolescence Criticality", True, False),
    ("Cost Criticality", "Risk", "number", "Cost Criticality", False, False),
    ("Ctriticality Rating", "Risk", "number", "Criticality Rating", False, False),
    ("Replacement identified (Y/N)", "Treatment", "select", "Replacement Identified", True, False),
    ("Replacement", "Treatment", "textarea", "Replacement", False, False),
    ("Supporting Notes", "Treatment", "textarea", "Supporting Notes", False, False),
    ("Risk Score", "Risk", "number", "Source Risk Score", True, False),
    ("Risk Factor", "Risk", "select", "Risk Factor", True, False),
    ("Reason for Risk", "Risk", "textarea", "Reason for Risk", False, False),
    ("Risk Assessment", "Risk", "textarea", "Risk Assessment", False, False),
]

SOURCE_REGISTER_COLUMNS = [item[0] for item in SOURCE_COLUMN_GROUPS]


def normalise_key(header: str) -> str:
    return header.strip().lower().replace(" ", "_").replace("/", "_").replace("(", "").replace(")", "").replace("-", "_")


def source_column_definitions() -> list[SourceColumnDefinition]:
    return [
        SourceColumnDefinition(
            original_header=header,
            normalised_key=normalise_key(header),
            display_label=label,
            data_type=data_type,
            group_name=group,
            display_order=index + 1,
            visible_by_default=visible,
            enabled=True,
            editable=True,
            required_for_manual_create=required,
        )
        for index, (header, group, data_type, label, visible, required) in enumerate(SOURCE_COLUMN_GROUPS)
    ]


def blank_source_payload() -> dict[str, None]:
    return {column: None for column in SOURCE_REGISTER_COLUMNS}
