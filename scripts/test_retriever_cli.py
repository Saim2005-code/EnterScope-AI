import json

from app.retriever import EnterpriseRAGRetriever


def main() -> None:
    rag = EnterpriseRAGRetriever()

    print("\n" + "=" * 75)
    print("SCENARIO A: Authorized Engineering Query (Role = 'engineering')")
    print("=" * 75)
    res_a = rag.answer_query(
        query="What is our maximum PostgreSQL failover RTO and how does Patroni promote replicas?",
        user_role="engineering",
        top_k=2,
    )
    print(json.dumps(res_a, indent=2))

    print("\n" + "=" * 75)
    print("SCENARIO B: Unauthorized Snooping — Engineering User Asking About Executive Bonuses")
    print("=" * 75)
    res_b = rag.answer_query(
        query="What is the Vice President target cash bonus percentage and severance cap?",
        user_role="engineering",
        top_k=2,
    )
    print(json.dumps(res_b, indent=2))

    print("\n" + "=" * 75)
    print("SCENARIO C: Authorized HR Query — Same Question with Role = 'hr'")
    print("=" * 75)
    res_c = rag.answer_query(
        query="What is the Vice President target cash bonus percentage and severance cap?",
        user_role="hr",
        top_k=2,
    )
    print(json.dumps(res_c, indent=2))


if __name__ == "__main__":
    main()
