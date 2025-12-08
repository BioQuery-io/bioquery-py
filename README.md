# BioQuery Python SDK

Python client for [BioQuery](https://bioquery.io) - natural language cancer genomics queries.

## Installation

```bash
pip install bioquery
```

## Quick Start

```python
import bioquery

# Initialize client
client = bioquery.Client(api_key="your-api-key")

# Ask a question in natural language
card = client.query("Is DDR1 expression higher in KIRP vs KIRC?")

# View the answer
print(card.answer)
# "DDR1 expression is significantly higher in KIRP compared to KIRC
#  (median 8.2 vs 5.1 TPM, p < 0.001, Wilcoxon rank-sum test)."

# Access statistical results
print(card.statistics)
# {'test': 'wilcoxon', 'p_value': 0.00012, 'effect_size': 0.45, ...}

# Display interactive figure
card.show_figure()

# Export
card.save_figure("ddr1_comparison.png")
card.to_dataframe()  # Get underlying data
```

## Features

- **Natural Language Queries**: Ask questions in plain English
- **Interactive Visualizations**: Plotly figures you can customize
- **Statistical Analysis**: Publication-ready p-values and effect sizes
- **Multiple Data Sources**: TCGA, TARGET, GTEx, CCLE, CPTAC, GENIE
- **Export Options**: PNG, SVG, JSON, DataFrame

## Example Queries

```python
# Differential expression
card = client.query("Compare BRCA1 expression in breast vs ovarian cancer")

# Tumor vs normal
card = client.query("Is TP53 higher in lung cancer vs normal lung tissue?")

# Survival analysis
card = client.query("Does high EGFR expression affect survival in lung adenocarcinoma?")

# Mutation frequency
card = client.query("What's the KRAS mutation rate across pancreatic cancer?")

# Cell lines
card = client.query("Show me BRAF expression across melanoma cell lines")
```

## Documentation

Full documentation: [docs.bioquery.io](https://docs.bioquery.io)

## License

MIT
