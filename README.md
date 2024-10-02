from venv import createfrom tracely import trace_event

# Tracely

Tracely is a tool for tracing and monitoring AI model interactions, allowing you to gain insights into how your models are performing in real-time. This repository provides a simple interface to integrate tracing into your Python applications.

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
    api_key="",                                      # ApiKey from Evidently Cloud 
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

After initialization of `tracely` you can decorate your function with `trace_event` to start collect traces of given function.

```python
from tracely import init_tracing
from tracely import trace_event


init_tracing()

@trace_event()
def process_request(question: str, session_id: str):
    # do work
    return "work done"
```

Decorator `trace_event` have several arguments:

- `span_name` - name of span to sent in event, default to function name
- `track_args` - list of function arguments to include in event, default to `None`, indicating to include all arguments
- `ingore_args` - list of function arguments to ignore, default to `None` - do not ignore anything
- `track_output` - do event should track function return value, default to `True`
- `parse_output` - do result should be parsed (dict, list and tuple types would be split in separate fields), default to `True`


#### Context Manager

If you need to create a trace event without decorate (eg, for a piece of code):

```python
from tracely import init_tracing
from tracely import create_trace_event


init_tracing()

with create_trace_event("external_span") as event:
    event.set_attribute("my-attribute", "value")
    # do work
    event.set_result({"data": "data"})
```

`create_trace_event` have arguments:

- `name` - event name to label it
- `parse_output` - do result (if set) should be parsed (dict, list and tuple types would be split in separate fields), default to `True`
- `**params` - kv-style params, to set as attributes

`event` object have methods:

- `set_attribute` - set a custom attribute
- `set_result` - set a result for an event, there can be only one result set for an event