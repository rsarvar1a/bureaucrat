use anyhow::{Error, Result};
use warp::{Filter, Rejection, Reply};

use crate::bureaucrat::{api, Configuration, Services};

/**
    Returns the filter for Bureaucrat's API, which is mounted at /api.
*/
pub fn get_routes() -> Result<impl Filter<Extract = impl Reply, Error = Rejection> + Clone, Error>
{
    let cfg = Configuration::get();
    let _services = Services::default();

    let routes =
        warp::path!("api").map(move || format!("Hello from the {} API!", cfg.clone().server.name));
    Ok(routes)
}
