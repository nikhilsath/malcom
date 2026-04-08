def execute_storage_step(connection, logger, *, step, context):
    """Execute `storage` automation step.

    Minimal placeholder implementation — real storage backends (S3, GCS,
    local) are implemented elsewhere. This function provides a stable
    importable symbol for the automation executor to call during modularization.
    """
    raise NotImplementedError("storage executor not yet implemented")
