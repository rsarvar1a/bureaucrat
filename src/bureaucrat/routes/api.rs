use warp::{Filter, Rejection, Reply};

use crate::bureaucrat::{Configuration, Services};

/**
    Returns the filter for Bureaucrat's API, which is mounted at /api.
*/
pub fn get_routes() -> impl Filter<Extract = impl Reply, Error = Rejection> + Clone
{
    let cfg = Configuration::get();
    let _services = Services::default();

    warp::path!("api").map(move || format!("Hello from the {} API!", cfg.clone().server.name))
}
