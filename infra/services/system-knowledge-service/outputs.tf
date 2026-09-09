output "service" {
  description = "System Knowledge Service deployment outputs."
  value       = try(module.system_knowledge_service[0].service, null)
}

output "identity" {
  description = "Dedicated non-executor workload identity."
  value       = try(module.system_knowledge_service[0].identity, null)
}

output "bot" {
  description = "Dedicated Azure Bot and Teams channel identifiers."
  value       = try(module.system_knowledge_service[0].bot, null)
}

output "claim_store" {
  description = "Content-free durable claim container identity."
  value       = try(module.system_knowledge_service[0].claim_store, null)
}

output "health_contract" {
  description = "Health contract used by protected post-deploy verification."
  value       = var.health
}

output "rollback_contract" {
  description = "Rollback contract used by protected deployment orchestration."
  value       = var.rollback
}
