"""
Wine Agent Quick Start Guide

This example demonstrates how to use the wine agent once tools are implemented.
Run this file to test the agent with your wine cellar cellar-data.
"""
from src.agents.intelligent.agent import create_wine_agent
from src.utils import logger


def main():
    """Quick start example for wine agent."""

    # Create agent
    print("Creating wine agent...")
    agent = create_wine_agent(verbose=True)
    print(f"✓ Agent created with {len(agent.get_available_tools())} tools")
    print()


    # # Generate and save the agent graph visualization
    # graph_png = agent.agent.get_graph(xray=True).draw_mermaid_png()
    #
    # # Save to file
    # with open("graph.png", "wb") as f:
    #     f.write(graph_png)
    #
    # print("✓ Agent graph saved to graph.png")
    # sys.exit()


    # Example queries to test
    test_queries = [
        #"What is the best red wines from Bordeaux that I have in my cellar?",
        "What is my favorite red wine from Romania?",
        # "Describe very shortly my taste profile.",
        #"What is malolactic fermentation?",
        # "Recommend a wine for grilled salmon",
        #"Show me my Burgundy wines",
    ]

    for i, query in enumerate(test_queries, 1):
        print(f"Query {i}: {query}")
        print()

        try:
            # Process query
            result = agent.invoke(query)

            # Display response
            print("Response:")
            print(result['final_answer'])

            # Show tools used (if verbose)
            if 'tools_used' in result:
                print(f"\nTools used: {', '.join(result['tools_used'])}")

        except Exception as e:
            print(f"Error: {e}")
            logger.exception("Query failed")

        print()
        print("-" * 60)
        print()


if __name__ == "__main__":
    main()



