import yaml


def load_semantic_layer(path="semantic_layer.yaml"):
    """Read the business definitions from the YAML file into a dictionary."""
    with open(path) as f:
        return yaml.safe_load(f)


def format_semantic_layer(layer):
    """Return the business definitions as text for the LLM: metrics, terms, then rules."""
    lines = ["Metrics:"]
    lines.extend([format_entry(metric) for metric in layer["metrics"]])
    lines.append("\nTerms:")
    lines.extend([format_entry(term) for term in layer["terms"]])
    lines.append("\nRules:")
    lines.extend([f"- {rule}" for rule in layer["rules"]])
    return "\n".join(lines)


def format_entry(entry):
    """Format one metric or term on one line; synonyms, joins and notes are optional."""
    line = f'- "{entry["name"]}"'
    if entry.get("synonyms"):
        line += f" (also: {', '.join(entry['synonyms'])})"
    line += f": {entry['sql']}"
    if entry.get("joins"):
        line += f". Joins: {entry['joins']}"
    if entry.get("notes"):
        line += f". {entry['notes']}"
    return line


if __name__ == "__main__":
    print(format_semantic_layer(load_semantic_layer()))
