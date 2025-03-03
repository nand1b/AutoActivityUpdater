
def activity_updater():
  
if __name__ == '__main__':
    try:
      activity_updater()
    except Exception as e:
        # printl("PrecipitationGrabber execution failed; printing exception: \n" + str(e))
        # printl("Full stack trace \n")
        traceback.print_exc()
