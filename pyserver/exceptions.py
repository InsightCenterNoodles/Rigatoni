class MethodException(Exception):
    
    def __init__(self, message='Method Could Not Be Invoked'):
        # Call the base class constructor with the parameters it needs
        super(MethodException, self).__init__(message)