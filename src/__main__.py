import dotenv

dotenv.load_dotenv(".env", override=True)

import bureaucrat
import os


def main():

    params = {k: os.environ.get(k, None) for k in ["LOG_LEVEL", "OWNER", "PREFIX"]}
    params = {k.lower(): v for k, v in params.items() if v is not None}

    bot = bureaucrat.Bureaucrat(**params)
    bot.run(os.getenv("DISCORD_TOKEN"))


if __name__ == "__main__":
    main()
