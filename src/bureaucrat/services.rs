
use crate::bureaucrat::Configuration;


#[derive(Clone)]
pub struct Services
{
    pub postgres: deadpool_postgres::Pool,
    pub redis: deadpool_redis::Pool
}

impl Default for Services
{   
    fn default() -> Self 
    {
        let postgres = create_postgres_pool();
        let redis = create_redis_pool();

        Services
        {
            postgres,
            redis
        }
    }
}

impl Services {}

fn create_postgres_pool() -> deadpool_postgres::Pool
{
    use deadpool_postgres::{Config, Runtime};
    use tokio_postgres::NoTls;

    let cfg = Configuration::get().postgres;
    let mut pgconfig = Config::new();
    pgconfig.url = Some(cfg.as_url());

    pgconfig.create_pool(Some(Runtime::Tokio1), NoTls).expect("failed to create Postgres pool")
}

fn create_redis_pool() -> deadpool_redis::Pool
{
    use deadpool_redis::{Config, Runtime};

    let cfg = Configuration::get().redis;
    let redisconfig = Config::from_url(cfg.as_url());

    redisconfig.builder()
        .expect("failed to create Redis pool builder")
        .max_size(cfg.max_connections)
        .runtime(Runtime::Tokio1)
        .build().expect("failed to create Redis pool")
}
