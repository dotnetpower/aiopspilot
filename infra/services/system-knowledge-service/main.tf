module "system_knowledge_service" {
  count  = var.enabled ? 1 : 0
  source = "./modules/system-knowledge-service"

  name            = var.name
  bot_name        = var.bot_name
  image           = var.image
  source_revision = var.source_revision
  platform        = var.platform
  teams           = var.teams
  claim_store     = var.claim_store
  health          = var.health
  rollback        = var.rollback
  runtime_env     = var.runtime_env
  scaling         = var.scaling
  tags            = var.tags
}
