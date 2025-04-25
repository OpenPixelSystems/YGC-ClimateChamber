# ClimateChamber Interface

A web-based control and monitoring system for a programmable climate chamber, enabling temperature profile management, real-time sensor data streaming, and experiment data logging. **Development is ongoing; expect further improvements and new features.**

---

## Features

- **Temperature Profile Control:**
  - Define, edit, and upload custom temperature cycles ("graphs") for the climate chamber.
  - Supports both constant temperature and time-dependent profiles.
- **Real-Time Monitoring:**
  - Live sensor data streaming via Server-Sent Events (SSE).
  - Visualization of current and target temperatures.
- **Manual Control:**
  - Override automatic control to set chamber temperature directly.
- **Data Logging & Database Viewer:**
  - Automatic logging of sensor data for each experiment cycle.
  - Web interface to view, export, and delete logged cycles.
- **Configurable PID Control:**
  - PID parameters (kp, ki, kd) and sensor read intervals are configurable.
  - Mock and real hardware support for development/testing.
- **Modular Backend:**
  - Flask-based backend with clear separation: routes, controllers, models, services.
  - Singleton state management for global app state.

---

## Architecture Overview

- **Backend:** Python (Flask)
  - `app/backend/controllers/`: Control logic (e.g., `ClimateChamberController` for PID and cycle management)
  - `app/backend/models/`: Hardware interfaces, mocks, and sensor modules
  - `app/backend/services/`: State, config, and temperature profile management
  - `app/routes/`: Flask blueprints for UI, API, and control endpoints
- **Frontend:** HTML/CSS/JS (in `app/templates/` and `app/static/`)
  - Responsive web UI for configuration, control, and data visualization
- **Database:** SQLite (default: `ClimateChamber_data.db`)

---

## Quick Start

### Prerequisites
- Python 3.8+
- `pip install -r requirements.txt`

### Running the Application
```bash
python run.py
```
- Access the web UI at: `http://localhost:5000`

---

## Main Endpoints
- `/` : Home/dashboard
- `/edit-config` : Edit configuration files
- `/setup-graph` : Create/edit temperature profiles
- `/display-graph` : Visualize active profile
- `/manual-control` : Manual override
- `/view-database` : View and manage logged cycles
- `/api/cycles`, `/api/data/<cycle_name>`, `/api/delete_cycle/<cycle_name>` : Database API

---

## Development Notes
- **Ongoing Improvements:**
  - Sensor module auto-discovery/configuration
  - Improved error handling and validation
  - More detailed logging and export options
  - Hardware abstraction for real/virtual chamber
- **Testing:**
  - Mock hardware classes for safe local development
- **Contribution:**
  - PRs and issues are welcome! Please document changes and follow modular design patterns.

---

## License
MIT (or specify your license)

---

## Contact
For questions or contributions, please contact the maintainers or open an issue on GitLab.

On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.
