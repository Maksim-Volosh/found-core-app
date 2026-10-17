class EmbeddingProviderUnavailableError(Exception):
    # Temporary failure of the provider (timeout, network, 429, 5xx): the job is retried.
    message = "Embedding provider is temporarily unavailable."

    def __init__(self) -> None:
        super().__init__(self.message)


class EmbeddingRejectedError(Exception):
    # Permanent failure (for example a rejected API key or a malformed vector): retrying cannot help.
    message = "Embedding provider rejected the request."

    def __init__(self) -> None:
        super().__init__(self.message)


class ProfileChangedDuringEmbeddingError(Exception):
    # The profile was edited after the worker read it, so the computed vector may not match the text. The job is retried.
    message = "Profile changed while its embedding was being computed."

    def __init__(self) -> None:
        super().__init__(self.message)
