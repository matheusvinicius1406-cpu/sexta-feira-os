# Adapter Layer — Sexta-Feira OS
#
# Every external interface (gRPC, REST, CLI) talks to the domain
# through adapters.  Adapters handle infrastructure concerns (DB
# sessions, owner lookup, error wrapping) so the domain stays pure.
#
#   gRPC Service → Adapter → Domain Service (Kernel)
#
# The adapter layer is the ONLY code that imports from:
#   - app.core.di      (Kernel singleton)
#   - app.db.database  (SessionLocal)
#   - app.models.models (SQLAlchemy models)
#
# No gRPC service, no REST router, no CLI script may import
# those modules directly.
