variable "observability_analyzer_image_update" {
  description = "Require the protected analyzer image updater to find its existing target."
  type        = bool
  default     = false
}

resource "terraform_data" "observability_analyzer_image_update" {
  triggers_replace = [var.core_image]

  provisioner "local-exec" {
    command     = "bash ../scripts/deployment/azure/update_analyzer_job_image.sh"
    working_dir = path.module
    environment = {
      DESIRED_IMAGE           = var.core_image
      REQUIRE_EXISTING_TARGET = tostring(var.observability_analyzer_image_update)
      TARGET_CONTAINER_NAME   = "analyzer-tick"
      TARGET_JOB_NAME         = "ca-${var.workload}${local.full_suffix}-core-analyzer"
      TARGET_RESOURCE_GROUP   = "rg-${var.workload}${local.full_suffix}"
    }
  }
}
