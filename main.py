from orchestrator import Orchestrator
from run_display import print_run_summary


if __name__ == "__main__":

    case = """
    A mid-sized supermarket chain in Spain is experiencing declining profit margins 
    despite stable revenue. Competition from discount retailers is intensifying. 
    Operational costs have increased due to supply chain inefficiencies.
    """

    orchestrator = Orchestrator(
    architecture="multi_agent_4",
    use_external_rag=True
    )

    result = orchestrator.run(case, case_id="case_001")

    print_run_summary(result)





