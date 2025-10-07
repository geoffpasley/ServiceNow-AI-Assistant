import _core.globe as globe
import _core.extension as extension
import _core.dependency as dependency
import process.process as process
import traceback

def main():

    # Initialize variables
    globe.Globe()

    # Check if the version of the application is correct
    try:
        a = dependency.Dependency().Check()
        if not a:
            globe.error = True
    except:
        traceback.print_exc()

    # Start the log messages
    try:
        globe.logger.start_msg()
    except:
        globe.error = True
        traceback.print_exc() 

    # Run the main process(es) 
    while (globe.error == False):
        try:
            p = process.Process().run()
            if not p:
                error = True
                break
        except Exception as e:
            error = True
            try:
                globe.logger.entry(str(e), type="error", state="end")
            except:
                traceback.print_exc()
        extension.Common().sleep(60)

    # End the log messages
    try:
        globe.logger.end_msg()
    except:
        traceback.print_exc() 

if __name__ == "__main__":
    main()