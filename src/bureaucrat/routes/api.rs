
use warp::{Filter, Rejection, Reply};


/**
    Returns the filter for Bureaucrat's API, which is mounted at /api.
*/
pub fn get_routes() -> impl Filter<Extract = impl Reply, Error = Rejection> + Clone
{
    warp::path!("api").map(|| "Hello from the Bureaucrat API!")
}
