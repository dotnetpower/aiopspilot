"""Notification-channel Protocols (Teams / Slack / Email / Webhook / PagerDuty / SMS).

Realizes the ``Channel`` contract in
[`docs/roadmap/interfaces/channels-and-notifications.md`](../../../../../docs/roadmap/interfaces/channels-and-notifications.md).
``core/`` sees only these Protocols and the router in
:mod:`fdai.core.notifications`; vendor SDKs (httpx, SMTP, ACS) sit
behind the concrete adapters under :mod:`fdai.delivery.notifications`.

Design points
-------------

- **One shape per channel, six typed Protocols.** Every adapter answers
  a single ``send(NotificationMessage) -> DeliveryReceipt`` call. Six
  Protocols keep the DI matrix statically typed - the router registers a
  ``TeamsChannel`` under the ``teams-*`` channel-ids and refuses to bind
  an :class:`EmailChannel` there.
- **Trust-tier lives on the message.** Every :class:`NotificationMessage`
  carries a :class:`TrustTier` (A1..A4) so the router can enforce the
  category-⊆-channel.categories rule without vendor knowledge.
- **Adapters never authorize.** ``awaitDecision`` (approval callback) is
  out of scope for the P1 router; ``send`` is send-only. Approval flows
  land in a later phase and re-enter through ``fdai-api``, matching
  the contract in the design doc.
- **Fakes ship in :mod:`~fdai.shared.providers.testing.notifications`**
  so both the router unit tests and downstream forks reuse them.
- **Capability-state and presentation are separate read-only contracts.**
  :mod:`.capability` reports availability/enablement/authority for a
  binding; :mod:`.presentation` is the pre-render, fail-closed redaction and
  bound boundary every renderer - including
  :class:`fdai.core.notifications.shadow.ShadowNotificationChannel` - MUST
  cross before formatting or sending.
"""

from .base import (
    ChannelAmbiguousError,
    ChannelDeliveryError,
    ChannelKind,
    ChannelUnavailableError,
    DeliveryReceipt,
    HilEscalationSink,
    Link,
    NotificationChannel,
    NotificationMessage,
    Severity,
    TrustTier,
)
from .capability import ChannelCapabilityState, ChannelMode
from .channels import (
    EmailChannel,
    PagerDutyChannel,
    SlackChannel,
    SmsChannel,
    TeamsChannel,
    WebhookChannel,
)
from .presentation import (
    INTERACTIVE_METADATA_KEYS,
    NotificationPresentationEnvelope,
    PresentationLimits,
    PresentationRejectedError,
    render_presentation,
)

__all__ = [
    "INTERACTIVE_METADATA_KEYS",
    "ChannelAmbiguousError",
    "ChannelCapabilityState",
    "ChannelDeliveryError",
    "ChannelKind",
    "ChannelMode",
    "ChannelUnavailableError",
    "DeliveryReceipt",
    "EmailChannel",
    "HilEscalationSink",
    "Link",
    "NotificationChannel",
    "NotificationMessage",
    "NotificationPresentationEnvelope",
    "PagerDutyChannel",
    "PresentationLimits",
    "PresentationRejectedError",
    "Severity",
    "SlackChannel",
    "SmsChannel",
    "TeamsChannel",
    "TrustTier",
    "WebhookChannel",
    "render_presentation",
]
