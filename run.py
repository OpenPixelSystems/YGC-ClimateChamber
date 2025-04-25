import app

ClimateChamberInterface = app.create_app()

if __name__ == '__main__':
    ClimateChamberInterface.run(host='0.0.0.0', port=5000)