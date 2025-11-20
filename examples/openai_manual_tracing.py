import asyncio
from time import sleep
from typing import Optional

import openai

import tracely
from tracely import UsageDetails
from tracely import init_tracing
from tracely import trace_event
from tracely import get_current_span

client = openai.Client()
async_cl = openai.AsyncClient()


@trace_event()
def call_openai(input: str) -> Optional[str]:
    response = client.responses.create(model="gpt-4.1", input=input)
    span = get_current_span()
    if response:
        span.update_usage(
            tokens={
                "input": response.usage.input_tokens,
                "output": response.usage.output_tokens,
            },
        )
        return response.output[0].content[0].text
    return None


@trace_event()
async def async_call_openai(input: str) -> Optional[str]:
    response = await async_cl.responses.create(model="gpt-4.1", input=input)
    span = get_current_span()
    if response:
        if span:
            span.update_usage(
                tokens={
                    "input": response.usage.input_tokens,
                    "output": response.usage.output_tokens,
                },
            )
        return response.output[0].content[0].text
    return None


@trace_event()
def call_openai_with_helper(input: str):
    response = client.responses.create(model="gpt-4.1", input=input)
    span = get_current_span()
    if response:
        span.update_usage(response.usage)
        return response.output[0].content[0].text
    return None


def call_openai_with_context(input: str):
    with tracely.create_trace_event("call_openai_with_context", input=input) as span:
        response = client.responses.create(model="gpt-4.1", input=input)
        if response:
            span.update_usage(response.usage)
            return response.output[0].content[0].text
        return None


@trace_event()
def multiple_calls_openai(input: str):
    answer = call_openai_with_helper(input)
    second_answer = call_openai_with_helper("Explain better this answer: " + answer)
    return second_answer


@trace_event()
def call_with_user_id_param(input: str, user_id: str):
    answer = call_openai_with_helper(input)
    second_answer = call_openai_with_helper("Explain better this answer: " + answer)
    return second_answer


@trace_event()
def call_with_user_id_explicit(input: str):
    span = get_current_span()
    span.setuser("user_id")
    answer = call_openai_with_helper(input)
    second_answer = call_openai_with_helper("Explain better this answer: " + answer)
    return second_answer


async def main():
    init_tracing(
        default_usage_details=UsageDetails(
            cost_per_token={"input": 2.0 / 1_000_000, "cached_input": 2.0 / 1_000_000, "output": 8.0 / 1_000_000}
        )
    )
    print(await async_call_openai("What is LLM?"))


if __name__ == "__main__":
    # init_tracing(
    #     default_usage_details=UsageDetails(
    #         cost_per_token={"input": 2.0 / 1_000_000, "cached_input": 2.0 / 1_000_000, "output": 8.0 / 1_000_000}
    #     )
    # )
    asyncio.run(main())
    # print(call_openai("What is LLM?"))
    # print(call_openai_with_helper("What is LLM?"))
    # print(call_openai_with_context("What is LLM?"))
    # print(multiple_calls_openai("What is LLM?"))
    # print(call_with_user_id_param("What is LLM?", "user_id"))
    # print(call_with_user_id_explicit("What is LLM?"))
    sleep(1)
