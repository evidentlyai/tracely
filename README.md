# Tracely

Tracely is a tool designed for tracing and monitoring AI model interactions, enabling you to gain real-time insights into your models' performance. This repository offers a straightforward interface for integrating tracing into your Python applications.

## Getting Started

### Prerequisites

- Python 3.x
- An account on [Evidently Cloud](https://app.evidently.cloud/)
- API Key from your Evidently account

### Installation

Tracely is available as a PyPI package. To install it using pip package manager, run:
```bash
pip install tracely
```


### Usage

#### Init

To send your traces to Evidently you need to initialize tracely:

```python
from tracely import init_tracing

init_tracing(
    address="https://app.evidently.cloud",           # Trace Collector Address
    api_key="",                                      # API Key from Evidently Cloud 
    team_id="a1d08c46-0624-49e3-a9f5-11a13b4a2aa5",  # Team ID from Evidently Cloud 
    export_name="tracing-dataset",
)
```

All parameters can be set using environment varialbes:

- `EVIDENTLY_TRACE_COLLECTOR` - trace collector address (default to https://app.evidently.cloud)
- `EVIDENTLY_TRACE_COLLECTOR_API_KEY` - API Key to access Evidently Cloud for creating dataset and uploading traces
- `EVIDENTLY_TRACE_COLLECTOR_EXPORT_NAME` - Export name in Evidently Cloud
- `EVIDENTLY_TRACE_COLLECTOR_TEAM_ID` - Team ID from Evidently Cloud to create Export dataset in

#### Decorator
Once Tracely is initialized, you can decorate your functions with `trace_event` to start collecting traces for a specific function:

```python
from tracely import init_tracing
from tracely import trace_event


init_tracing()

@trace_event()
def process_request(question: str, session_id: str):
    # do work
    return "work done"
```
The `trace_event` decorator accepts several arguments:

- `span_name` - the name of the span to send in the event (defaults to the function name)
- `track_args` - a list of function arguments to include in the event (defaults to `None`, indicating that all arguments should be included)
- `ingore_args` - a list of function arguments to exclude (defaults to `None`, meaning no arguments are ignored)
- `track_output` - indicates whether the event should track the function's return value (defaults to `True`)
- `parse_output` - indicates whether the result should be parsed (e.g., dict, list, and tuple types would be split into separate fields; defaults to `True`)

#### Context Manager

If you need to create a trace event without using a decorator (e.g., for a specific piece of code), you can do so with the context manager:

```python
from tracely import init_tracing
from tracely import create_trace_event


init_tracing()

with create_trace_event("external_span") as event:
    event.set_attribute("my-attribute", "value")
    # do work
    event.set_result({"data": "data"})
```

The `create_trace_event` function accepts the following arguments:

- `name` - the name of the event to label it
- `parse_output` - indicates whether the result (if set) should be parsed (dict, list and tuple types would be split in separate fields), default to `True`
- `**params` - key-value style parameters to set as attributes

The `event` object has the following methods:

- `set_attribute` - set a custom attribute for the event
- `set_result` - set a result for the event (only one result can be set per event)
