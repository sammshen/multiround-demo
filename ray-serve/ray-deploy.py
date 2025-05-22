from ray import serve
from ray.serve.llm import LLMConfig, build_openai_app

llm_config = LLMConfig(
    model_loading_config=dict(
        model_id="meta-llama/Llama-3.1-8B-Instruct",
        model_source="meta-llama/Llama-3.1-8B-Instruct",
    ),
    deployment_config=dict(
        autoscaling_config=dict(
            min_replicas=2, max_replicas=2,
        )
    ),
    # Pass the desired accelerator type (e.g. A10G, L4, etc.)
    accelerator_type="H100",
    # You can customize the engine arguments (e.g. vLLM engine kwargs)
    engine_kwargs=dict(
        tensor_parallel_size=1,
    ),
    runtime_env=dict(
        env_vars=dict(
            HF_TOKEN="<YOUR_HF_TOKEN>"
        )
    )
)


# Start Serve with a custom port
serve.start(http_options={"port": 30081})

app = build_openai_app({"llm_configs": [llm_config]})
serve.run(app, blocking=True)