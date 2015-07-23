**HEADS-UP: Needs OctoPrint 1.2.4 or later!**

# OctoPrint Pushbullet Plugin

This is an OctoPrint Plugin that adds support for [Pushbullet notifications](https://www.pushbullet.com/) to OctoPrint.

At the current state OctoPrint will send a notification when a print job finishes. If a webcam is available, an image
of the print result will be captured and included in the notification.

![Configuration Dialog](http://i.imgur.com/7WYe8E9.png)

![Example Push Notification](http://i.imgur.com/EyfOuVZ.png)

## Installation

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager) 
or manually using this URL and the ``--process-dependency-links`` option:

    https://github.com/OctoPrint/OctoPrint-Pushbullet/archive/master.zip

## Configuration

The only thing that absolutely needs to be configured is the Access Token necessary to access Pushbullet's API. You
can find this in you Pushbullet Account Settings under "Access Token". Copy and paste the value there into the
"Access Token" input field in the configuration dialog of the Pushbullet plugin.

By manually editing `config.yaml` it is also possible to adjust the text of the message that will be sent in the notification.

``` yaml
plugins:
  octobullet:
    # Pushbullet Access Token for your account
    access_token: your_access_token
    
    # message to send when a print is done
    # available placeholders:
    # - file: name of the file that was printed
    # - elapsed_time: duration of the print in HH:mm:ss format
    printDone:
      # title of the notification
      title: 'Print job finished'
      
      # body of the notification
      body: '{file} finished printing in {elapsed_time}'
```

