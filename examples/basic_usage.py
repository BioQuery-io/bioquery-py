"""Basic usage example for BioQuery Python SDK."""

import bioquery


def main() -> None:
    """Demonstrate basic BioQuery SDK usage."""
    # Initialize client (API key from env or explicit)
    client = bioquery.Client()

    # Submit a natural language query
    print("Submitting query...")
    card = client.query("Is DDR1 expression higher in KIRP vs KIRC?")

    # Access the results
    print(f"\nCard ID: {card.card_id}")
    print(f"\nQuestion: {card.question}")
    print(f"\nInterpretation: {card.interpretation}")
    print(f"\nAnswer: {card.answer}")

    # Access statistics
    if card.statistics:
        print(f"\nStatistics:")
        print(f"  P-value: {card.p_value}")
        print(f"  Effect size: {card.effect_size}")

    # Display the figure (in Jupyter)
    # card.show_figure()

    # Save the figure
    # card.save_figure("output.png")

    # Get underlying data as DataFrame
    # df = card.to_dataframe()
    # print(df.head())

    # Export full card as JSON
    # print(card.to_json())

    client.close()


if __name__ == "__main__":
    main()
