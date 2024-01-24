use anyhow::{Error, Result};
use warp::{Filter, Rejection, Reply};

/**
 Returns the Svelte frontend as a static site.
*/
pub fn get_routes() -> Result<impl Filter<Extract = impl Reply, Error = Rejection> + Clone, Error>
{
    let routes = warp::path("app").and(static_dir::static_dir!("client/dist"));
    Ok(routes)
}
