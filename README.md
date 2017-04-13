**HEADS-UP: Needs OctoPrint 1.2.4 or later!**

# OctoPrint Pushbullet Plugin

This is an OctoPrint Plugin that adds support for [Pushbullet notifications](https://www.pushbullet.com/) to OctoPrint.

At the current state OctoPrint will send a notification when a print job finishes. If a webcam is available, an image
of the print result will be captured and included in the notification.

![Configuration Dialog](http://i.imgur.com/7WYe8E9.png)

![Example Push Notification](http://i.imgur.com/EyfOuVZ.png)

## Installation

Install via the bundled [Plugin Manager](https://github.com/foosel/OctoPrint/wiki/Plugin:-Plugin-Manager) 
or manually using this URL:

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

## Known Issues

### The test message fails but my access token definitely is correct

Check your `octoprint.log`. If it contains an error that looks like this:

    2017-04-12 09:59:35,161 - octoprint.plugins.octobullet - ERROR - Error while instantiating PushBullet
    Traceback (most recent call last):
      File "/home/pi/oprint/local/lib/python2.7/site-packages/octoprint_octobullet/__init__.py", line 214, in _create_sender
        bullet = pushbullet.PushBullet(token)
      File "/home/pi/oprint/local/lib/python2.7/site-packages/pushbullet/pushbullet.py", line 29, in __init__
        self.refresh()
      File "/home/pi/oprint/local/lib/python2.7/site-packages/pushbullet/pushbullet.py", line 288, in refresh
        self._load_devices()
      File "/home/pi/oprint/local/lib/python2.7/site-packages/pushbullet/pushbullet.py", line 42, in _load_devices
        resp_dict = self._get_data(self.DEVICES_URL)
      File "/home/pi/oprint/local/lib/python2.7/site-packages/pushbullet/pushbullet.py", line 32, in _get_data
        resp = self._session.get(url)
      File "/home/pi/oprint/local/lib/python2.7/site-packages/requests-2.7.0-py2.7.egg/requests/sessions.py", line 477, in get
        return self.request('GET', url, **kwargs)
      File "/home/pi/oprint/local/lib/python2.7/site-packages/requests-2.7.0-py2.7.egg/requests/sessions.py", line 465, in request
        resp = self.send(prep, **send_kwargs)
      File "/home/pi/oprint/local/lib/python2.7/site-packages/requests-2.7.0-py2.7.egg/requests/sessions.py", line 573, in send
        r = adapter.send(request, **kwargs)
      File "/home/pi/oprint/local/lib/python2.7/site-packages/requests-2.7.0-py2.7.egg/requests/adapters.py", line 431, in send
        raise SSLError(e, request=request)
    SSLError: [Errno 8] _ssl.c:504: EOF occurred in violation of protocol

your version of Python and hence its built-in SSL support is too old to
work together with the Pushbullet API. This affects Python versions less
than 2.7.9. If you are still running OctoPi 0.12 which was based on
Raspbian Wheezy, you only have Python 2.7.3 and this is the likely cause.

This can be fixed though. The following steps assume you are indeed running
OctoPi - if not please substitute your virtual environment path (`~/oprint`
here) accordingly or better yet, update your Python version to at least
2.7.9.

SSH into OctoPi. Then execute the following:

    sudo apt-get update
    sudo apt-get install libffi-dev
    source ~/oprint/bin/activate
    pip install requests[security]
    sudo service octoprint restart

This might take a bit since a bunch of security libraries have to be
installed, at least one of which also needs compilation. On a Pi2 it takes
a couple of minutes. After the restart of OctoPrint your problems
should vanish.

What are those commands doing? They basically update the SSL support for
the library the Pushbullet plugin is using to talk to the Pushbullet API.
And why can't Pushbullet detect this and solve on its own? The problem is
that bit with `libffi-dev` up there - that's a dependency needed for the
updated library to successfully build on your system, and the plugin
can't install that for you.