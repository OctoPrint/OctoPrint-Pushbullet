$(function() {
    function OctobulletViewModel(parameters) {
        var self = this;

        self.settings = parameters[0];

        self.busy = ko.observable(false);
        
        self.sendTestMessage = function() {
            self.busy(true);
            $.ajax({
                url: API_BASEURL + "plugin/octobullet",
                type: "POST",
                dataType: "json",
                data: JSON.stringify({
                    command: "test",
                    token: self.settings.settings.plugins.octobullet.access_token(),
                    channel: self.settings.settings.plugins.octobullet.push_channel()
                }),
                contentType: "application/json; charset=UTF-8",
                success: function(response) {
                    self.busy(false);
                    if (response.result) {
                        new PNotify({
                            title: gettext("Test message sent"),
                            text: gettext("A test message was sent to Pushbullet"),
                            type: "success"
                        });
                    } else {
                        new PNotify({
                            title: gettext("Test message could not be sent"),
                            text: gettext("Test message could not be sent to Pushbullet, check settings"),
                            type: "error"
                        });
                    }
                },
                error: function() {
                    self.busy(false);
                }
            });
        };
    }

    ADDITIONAL_VIEWMODELS.push([
        OctobulletViewModel,
        ["settingsViewModel"],
        ["#settings_plugin_octobullet"]
    ]);
});
