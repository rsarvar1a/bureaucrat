mod auth;
pub mod configuration;
mod routes;
mod services;

/* Required by main */

pub use configuration::Configuration;
pub use routes::get_routes;

/* Internals */

use services::Services;
