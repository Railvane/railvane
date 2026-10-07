"""Lifecycle catalogue: phases and areas a guardrail can belong to.

The `area` frontmatter field must be one of the area ids below. The catalogue
is advisory: not every area needs guardrails.
"""

PHASES: dict[str, dict] = {
    "idea": {"name": "Idea & discovery", "areas": {
        "ideation": "Ideation & intake",
        "requirements": "Product & requirements",
        "priority": "Prioritisation & roadmap",
    }},
    "design": {"name": "Design", "areas": {
        "architecture": "Architecture",
        "ux": "UX / UI design",
        "data": "Data model & storage",
        "api": "API design",
    }},
    "build": {"name": "Build", "areas": {
        "coding": "Coding standards",
        "stack": "Language & stack specifics",
        "git": "Git & branching",
        "review": "Code review",
        "deps": "Dependencies",
        "ai": "AI assistance",
    }},
    "quality": {"name": "Quality & security", "areas": {
        "testing": "Testing",
        "security": "Security",
        "privacy": "Privacy & compliance",
        "i18n": "Accessibility & i18n",
    }},
    "release": {"name": "Release & deploy", "areas": {
        "cicd": "CI/CD",
        "versioning": "Release & versioning",
        "deploy": "Deploy & environments",
        "config": "Configuration & environment",
    }},
    "ops": {"name": "Operations", "areas": {
        "monitoring": "Monitoring & observability",
        "incident": "Incident management",
        "backup": "Backup & recovery",
        "maintenance": "Maintenance & lifecycle",
        "docs": "Documentation & knowledge",
    }},
}

# area id -> phase id
AREA_PHASE: dict[str, str] = {
    area: phase for phase, p in PHASES.items() for area in p["areas"]
}
