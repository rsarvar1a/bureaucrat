mod api;
mod discord;
mod routes;

pub mod configuration;
pub mod models;
pub mod services;

/* Required by main */

pub use configuration::Configuration;
pub use discord::create_client;
pub use routes::get_routes;

/* Internals */

use services::Services;
