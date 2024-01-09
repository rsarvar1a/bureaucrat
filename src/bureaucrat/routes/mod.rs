
mod api;
mod app;

use warp::{http::Uri, Filter, Rejection, Reply};


/**
 Returns Bureaucrat's routes.
*/
pub fn get_routes() -> impl Filter<Extract = impl Reply, Error = Rejection> + Clone
{
    let cors = warp::cors()
        .allow_any_origin()
        .allow_methods(vec!["GET", "POST", "HEAD"])
        .allow_headers(vec!["Content-Type"])
        .build();
    
    // Redirect the root to the app, but 404 on anything else, I guess?

    warp::path::end()
        .map(|| warp::redirect::found(Uri::from_static("/app/")))
        .or(api::get_routes())
        .or(app::get_routes())
        .with(cors)
}
