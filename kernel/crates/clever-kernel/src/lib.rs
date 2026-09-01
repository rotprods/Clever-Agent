#![forbid(unsafe_code)]

pub mod actions;
pub mod audit;
pub mod capabilities;
pub mod error;
pub mod events;
pub mod identity;
pub mod lifecycle;
pub mod policy;
pub mod version;

use actions::ActionStore;
use audit::AuditLog;
use capabilities::CapabilityRegistry;
use events::EventRouter;
use lifecycle::RuntimeHealthTracker;
use policy::PolicyBroker;

/// The CP02 kernel is deliberately a control-plane composition root only.
/// Native runtime/provider/channel/device implementations remain in adapters.
pub struct Kernel<P: PolicyBroker> {
    pub capabilities: CapabilityRegistry,
    pub events: EventRouter,
    pub policy: P,
    pub actions: ActionStore,
    pub audit: AuditLog,
    pub runtime_health: RuntimeHealthTracker,
}

impl<P: PolicyBroker> Kernel<P> {
    #[must_use]
    pub fn new(policy: P) -> Self {
        Self {
            capabilities: CapabilityRegistry::default(),
            events: EventRouter::default(),
            policy,
            actions: ActionStore::default(),
            audit: AuditLog::default(),
            runtime_health: RuntimeHealthTracker::default(),
        }
    }
}
