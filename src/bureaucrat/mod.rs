mod api;
pub mod configuration;
mod discord;
mod models;
mod routes;
mod services;

/* Required by main */

pub use configuration::Configuration;
pub use discord::create_client;
pub use routes::get_routes;

/* Internals */

use services::Services;
