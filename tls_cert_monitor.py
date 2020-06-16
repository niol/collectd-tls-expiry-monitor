"""Retrieves the expiry of certificates from a list of hosts"""
import datetime
import socket
import ssl

import collectd


PLUGIN_NAME = 'tls-cert-monitor'
INTERVAL = 10  # seconds


def configure(configobj):
    '''Configure this plugin based on collectd.conf parts.

    Example configuration:

    LoadPlugin python
    ...
    <Plugin python>
        ModulePath "/usr/local/lib/collectd/python/"
        LogTraces true
        Interactive false
        Import "tls_cert_monitor"
        <Module tls_cert_monitor>
            hosts "github.com" "google.com"
        </Module>
    </Plugin>
    '''
    # pylint: disable=C0103,W0603
    global _hosts

    collectd.info(
        'tls-cert-monitor: Configure with: key=%s, children=%r' %
        (configobj.key, configobj.children))

    config = {c.key: c.values for c in configobj.children}

    collectd.info('tls-cert-monitor: Configured with %r' % (config))

    # Set a module-global based on external configuration
    _hosts = config.get('hosts')


def ssl_expiry_datetime(hostname):
    """Get expiry date of cert's."""
    context = ssl.create_default_context()
    conn = context.wrap_socket(
        socket.socket(socket.AF_INET),
        server_hostname=hostname,
    )

    # 3 second timeout
    conn.settimeout(3.0)
    conn.connect((hostname, 443))

    ssl_info = conn.getpeercert()
    ssl_date_fmt = r'%b %d %H:%M:%S %Y %Z'

    # parse the string from the certificate into a Python datetime object
    return datetime.datetime.strptime(ssl_info['notAfter'], ssl_date_fmt)


def ssl_valid_time_remaining(hostname):
    """Get the number of days left in a cert's lifetime."""
    try:
        expires = ssl_expiry_datetime(hostname)
    except ssl.SSLError:
        return datetime.timedelta(0)
    return expires - datetime.datetime.utcnow()


# Data is required
def read():
    """Export number of days left to collectd."""
    for host in _hosts:
        remaining = ssl_valid_time_remaining(host)
        remaining = remaining.total_seconds()
        remaining = int(remaining)

        collectd.info(
            'tls-cert-monitor(host=%s): Reading data (data=%d)' %
            (host, remaining))

        val = collectd.Values(type='gauge', type_instance=host)

        val.plugin = 'tls-cert-monitor'
        val.dispatch(values=[remaining])


# Use a global variable here because we love python
_hosts = None

collectd.info('tls-cert-monitor: Loading Python plugin: ' + PLUGIN_NAME)
collectd.register_config(configure)
collectd.register_read(read, INTERVAL)
