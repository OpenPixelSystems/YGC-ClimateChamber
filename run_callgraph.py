from pycallgraph2 import Config
from pycallgraph2 import PyCallGraph
from pycallgraph2.output import GraphvizOutput
from pycallgraph2.globbing_filter import GlobbingFilter

config = Config()
config.trace_filter = GlobbingFilter(include=[
    'app.*',  # Only include your application code
])

graphviz = GraphvizOutput()
graphviz.output_file = 'callgraph.png'

with PyCallGraph(output=graphviz, config=config):
    import app
    ClimateChamberInterface = app.create_app()
    ClimateChamberInterface.run(host='0.0.0.0', port=5000, debug=False)