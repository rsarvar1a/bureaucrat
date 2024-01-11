use warp::{Filter, Rejection, Reply};

/**
 Returns the Svelte frontend as a static site.
*/
pub fn get_routes() -> impl Filter<Extract = impl Reply, Error = Rejection> + Clone
{
    warp::path("app").and(static_dir::static_dir!("client/dist"))
}
