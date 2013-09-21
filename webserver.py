import web
import task_handler as handler
import task
import inspect
import ConfigParser

config = ConfigParser.ConfigParser()
config.read('workflow.cfg')

bind_address = config.get('server', 'bind_address')
bind_port = int(config.get('server', 'bind_port'))

class WorkflowApplication(web.application):
    def run(self, port=8080, *middleware):
        func = self.wsgifunc(*middleware)
        return web.httpserver.runsimple(func, (bind_address, bind_port))

task.initialize()
urls = (
	'/callback', 'callback',
	'/accept', 'accept',
	'/decline', 'decline',
	'/multiple', 'multiple',
    '/upload_amazon', 'upload_amazon'
)

app = WorkflowApplication(urls, globals())

class callback:
    def POST(self):
        data = web.data()
        handler.new_tasks(data)

class accept:
    def GET(self):
        web.header('Content-Type', 'text/html')
    	get_var = web.input(task = 'task')
    	response = handler.accept_task(web.websafe(get_var.task), False)
    	if response['code'] == '404':
    		web.notfound()
    	if response['code'] == '410':
    		web.gone()
    	return response['html']


class decline:
    def GET(self):
        web.header('Content-Type', 'text/html')
    	get_var = web.input(task = 'task')
        response = handler.decline_task(web.websafe(get_var.task), False)	
        if response['code'] == '404':
            web.notfound()
        if response['code'] == '410':
            web.gone()
        return response['html']

class multiple:
    def GET(self):
        web.header('Content-Type', 'text/html')
        get_vars = web.input()
        response = handler.multiple_update(web.websafe(get_vars.tasks), web.websafe(get_vars.action), web.websafe(get_vars.dc))
        if response['code'] == '404':
            web.notfound()
        if response['code'] == '410':
            web.gone()
        return response['html']

class upload_amazon:
    def GET(self):
        web.header('Content-Type', 'text/html')
        get_vars = web.input()
        response = handler.upload_amazon(web.websafe(get_vars.task), web.websafe(get_vars.dc))
        if response['code'] == '404':
            web.notfound()
        if response['code'] == '410':
            web.gone()
        return response['html']

if __name__ == '__main__':
	app.run()
