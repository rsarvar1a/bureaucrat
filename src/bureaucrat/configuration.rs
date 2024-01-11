use anyhow::{Context, Error, Result};
use derivative::Derivative;
use lazy_static::lazy_static;
use serde::Deserialize;

use std::default::Default;
use std::sync::RwLock;


#[derive(Clone, Debug, Default, Deserialize)]
pub struct DiscordConfiguration
{
    pub client_id: String,
    pub client_secret: String
}


#[derive(Clone, Debug, Derivative, Deserialize)]
#[derivative(Default)]
pub struct PostgresConfiguration
{
    #[derivative(Default(value="\"localhost\".to_owned()"))]
    pub host: String,

    #[derivative(Default(value="\"5432\".to_owned()"))]
    pub port: String,

    pub username: String,
    pub password: String,
    pub database: String,
}

impl PostgresConfiguration
{
    /**
     Returns the Postgres schema URL to the database. 
    */
    pub fn as_url(& self) -> String
    {
        static SCHEMA : &str = "postgresql://";

        let location = format!(
            "{schema}{user}{auth_separator}{pass}{at_sign}{host}{port_separator}{port}",
            schema = SCHEMA,
            user = self.username,
            pass = self.password, 
            host = self.host, 
            port = self.port, 
            auth_separator = match self.password.as_str() { "" => "", _ => ":" },
            at_sign = match self.username.as_str() { "" => "", _ => "@" },
            port_separator = match self.port.as_str() { "" => "", _ => ":" }
        );

        format!(
            "{location}{database_separator}{database}",
            location = location,
            database = self.database,
            database_separator = match self.database.as_str() == "" || location.as_str() == SCHEMA { true => "", false => "/" }
        )
    }
}


#[derive(Clone, Debug, Derivative, Deserialize)]
#[derivative(Default)]
pub struct RedisConfiguration
{
    #[derivative(Default(value="\"localhost\".to_owned()"))]
    pub host: String,

    #[derivative(Default(value="\"6379\".to_owned()"))]
    pub port: String,

    pub username: String,
    pub password: String,
    pub database: String,
    
    pub max_connections: usize
}

impl RedisConfiguration
{
    /**
     Returns the Postgres schema URL to the database. 
    */
    pub fn as_url(& self) -> String
    {
        static SCHEMA : &str = "redis://";

        let location = format!(
            "{schema}{user}{auth_separator}{pass}{at_sign}{host}{port_separator}{port}",
            schema = SCHEMA,
            user = self.username,
            pass = self.password, 
            host = self.host, 
            port = self.port, 
            auth_separator = match self.password.as_str() { "" => "", _ => ":" },
            at_sign = match self.username.as_str() { "" => "", _ => "@" },
            port_separator = match self.port.as_str() { "" => "", _ => ":" }
        );

        format!(
            "{location}{database_separator}{database}",
            location = location,
            database = self.database,
            database_separator = match self.database.as_str() == "" || location.as_str() == SCHEMA { true => "", false => "/" }
        )
    }
}


#[derive(Clone, Debug, Deserialize)]
pub struct ServerConfiguration
{
    pub name: String,
    pub host: String,
    pub port: usize,
    pub use_tls: bool,
    pub tls_pem: String,
    pub tls_key: String
}

impl Default for ServerConfiguration
{
    fn default() -> Self 
    {
        ServerConfiguration 
        {  
            name: "Bureaucrat".to_owned(),
            host: "127.0.0.1".to_owned(),
            port: 3001,
            use_tls: false,
            tls_pem: "".to_owned(),
            tls_key: "".to_owned()
        }
    }
}

impl ServerConfiguration
{
    pub fn as_addr(& self) -> String
    {
        format!("{}:{}", self.host, self.port)
    }
}


#[derive(Clone, Debug, Derivative, Deserialize)]
#[derivative(Default)]
#[serde(default)]
pub struct Configuration
{
    #[derivative(Default(value="false"))]
    pub debug: bool,
    
    pub discord: DiscordConfiguration,
    pub postgres: PostgresConfiguration,
    pub redis: RedisConfiguration,
    pub server: ServerConfiguration
}

impl Configuration
{
    /**
     Initializes the global configuration. The source flow is as follows: 
     1. the config path specified,
     2. the `.env` file, and
     3. any environment variables with the `BUREAUCRAT_` prefix.
    */
    pub fn initialize(config_path: &str) -> Result<(), Error>
    {
        let source = config::Config::builder()
            .add_source(config::File::with_name(config_path).required(false))
            .add_source(config::File::with_name(".env").required(false))
            .add_source(config::Environment::with_prefix("bureaucrat"))
            .build()
            .context("failed to collect from sources")?;

        let config = source.try_deserialize()
            .context("failed to deserialize config")?;

        let mut global_config = CONFIG.write().unwrap();
        * global_config = config;
        Ok(())
    }

    /**
     * Retrieves the global configuration.
     */
    pub fn get() -> Configuration
    {
        CONFIG.read().unwrap().to_owned()
    }
}

lazy_static!
{
    static ref CONFIG: RwLock<Configuration> = RwLock::new(Configuration::default());
}
