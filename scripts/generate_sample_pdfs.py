from pathlib import Path

import pymupdf as fitz

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

SAMPLE_DOCS = {
    "eng_system_design.pdf": [
        (
            "Page 1: Core Microservices & gRPC Architecture\n\n"
            "Section 1.1: Internal Service Communication.\n"
            "All tier-1 backend microservices must communicate via gRPC over HTTP/2 using "
            "Protocol Buffers v3. REST/JSON is strictly restricted to public-facing API gateways. "
            "The p99 latency SLA for internal gRPC calls between the Order Service and Inventory "
            "Service is capped at 15 milliseconds under a sustained load of 10,000 requests per second."
        ),
        (
            "Page 2: High Availability & Database Failover Runbook\n\n"
            "Section 2.1: PostgreSQL Recovery Time Objective (RTO).\n"
            "According to production architecture guidelines, the maximum Recovery Time Objective "
            "(RTO) for primary PostgreSQL database failover is strictly capped at 30 seconds. "
            "Recovery Point Objective (RPO) is zero data loss via synchronous WAL replication.\n\n"
            "Section 2.2: Automated Replica Promotion.\n"
            "When the primary PostgreSQL node fails health checks for 3 consecutive pings (at a "
            "10-second interval), Patroni automatically promotes the lowest-lag synchronous standby "
            "replica to primary and updates the PgBouncer routing table within 5 seconds."
        ),
    ],
    "hr_executive_comp.pdf": [
        (
            "Page 1: Confidential Executive Compensation & Bonus Structure (2026)\n\n"
            "Section 1.1: Annual Performance Bonus Tiers.\n"
            "Vice Presidents (Level E8) and Senior Directors (Level E7) are eligible for an annual "
            "target cash bonus equal to 45% of base salary, scaling up to a 1.8x multiplier if "
            "company EBITDA exceeds annual targets by 15%.\n\n"
            "Section 1.2: Executive Equity Refreshers.\n"
            "Annual RSU refresh grants vest over a 4-year schedule with a 1-year cliff (25% after "
            "12 months, followed by 6.25% quarterly vesting thereafter)."
        ),
        (
            "Page 2: Involuntary Termination & Severance Policy\n\n"
            "Section 2.1: Severance Package Calculation.\n"
            "In the event of a workforce reduction or restructuring without cause, full-time employees "
            "receive a base severance payout of 8 weeks of base salary, plus 2 additional weeks "
            "for every completed year of continuous service, capped at a maximum of 26 weeks. "
            "COBRA health insurance premiums are subsidized at 100% by the company for 6 months."
        ),
    ],
}


def create_pdfs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    for filename, pages in SAMPLE_DOCS.items():
        pdf_path = DATA_DIR / filename
        doc = fitz.open()
        for page_text in pages:
            page = doc.new_page()
            rect = fitz.Rect(50, 50, 550, 750)
            page.insert_textbox(rect, page_text, fontsize=11, fontname="helv")
        doc.save(pdf_path)
        doc.close()
        print(f"[+] Generated sample PDF: {pdf_path.name} ({len(pages)} pages)")


if __name__ == "__main__":
    create_pdfs()
