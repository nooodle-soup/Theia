from dotenv import dotenv_values

config = {
    **dotenv_values(".env.shared"),  # load shared development variables
    **dotenv_values(".env.secret"),  # load sensitive variables
}


if config['USERNAME'] == 'None':
    pass

if config['PASSWORD'] == 'None':
    pass
