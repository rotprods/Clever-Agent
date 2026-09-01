#![forbid(unsafe_code)]

pub mod capabilities;
pub mod error;
pub mod events;
pub mod identity;
pub mod policy;
pub mod version;

use capabilities::CapabilityRegistry;
use events::EventRouter;
use policy::PolicyBroker;

/// The CP02 kernel is deliberately a control-plane composition root only.
/// Native runtime/provider/channel/device implementations remain in adapters.
pub struct Kernel<P: PolicyBroker> {
    pub capabilities: CapabilityRegistry,
    pub events: EventRouter,
    pub policy: P,
}

impl<P: PolicyBroker> Kernel<P> {
    #[must_use]
    pub fn new(policy: P) -> Self {
        Self {
            capabilities: CapabilityRegistry::default(),
            events: EventRouter::default(),
            policy,
        }
    }
}
