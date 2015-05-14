import re
from lxml import etree
from lxml.builder import E

try:
    from xmltodict import LXMLParser
except:
    class LXMLParser(object):
        def __init__(self, *args, **kwargs):
            pass
        def __call__(self, *args, **kwargs):
            raise ValueError("xmltodict not found, or does not contain the LXMLParser class; therefore, \"dict\" format is not available. Install an appropriate version of xmltodict to gain access to use the \"dict\" format.")

class _RpcMetaExec(object):

    # -----------------------------------------------------------------------
    # CONSTRUCTOR
    # -----------------------------------------------------------------------

    def __init__(self, junos):
        """
          ~PRIVATE CLASS~
          creates an RPC meta-executor object bound to the provided
          ez-netconf :junos: object
        """
        self._junos = junos
        self._lxmlparseropts = dict(new_style=True,
                                    index_keys_compress=False,
                                    index_keys=('name',))
        self._lxmlparser = LXMLParser(**self._lxmlparseropts)

    # -----------------------------------------------------------------------
    # lxmlparseropts property
    # -----------------------------------------------------------------------
    @property
    def lxmlparseropts(self):
        """
        The options that are passed to xmltodict.LXMLParser when
        creating a dict from RPC output.
        """
        return self._lxmlparseropts

    @lxmlparseropts.setter
    def lxmlparseropts(self, value):
        try:
            self._lxmlparser = LXMLParser(**value)
            self._lxmlparseropts = value
        except:
            raise

    # -----------------------------------------------------------------------
    # get_config
    # -----------------------------------------------------------------------

    def get_config(self, filter_xml=None, _format='xml', options={}):
        """
        retrieve configuration from the Junos device

        :filter_xml: is options, defines what to retrieve.  if omitted then the entire configuration is returned

        :options: is a dict, creates attributes for the RPC

        """
        rpc = E('get-configuration', options)

        if filter_xml is not None:
            # wrap the provided filter with toplevel <configuration> if
            # it does not already have one
            cfg_tag = 'configuration'
            at_here = rpc if cfg_tag == filter_xml.tag else E(cfg_tag)
            at_here.append(filter_xml)
            if at_here is not rpc: rpc.append(at_here)

        rv = self._junos.execute(rpc)
        if _format == 'xml':
            return rv
        elif _format == 'dict':
            return self._lxmlparser(rv)
        else:
            raise ValueError("Unknown format \"%s\" (expected \"xml\" or \"dict\")" % _format)

    # -----------------------------------------------------------------------
    # load_config
    # -----------------------------------------------------------------------

    def load_config(self, contents, **options):
        """
        loads :contents: onto the Junos device, does not commit the change.

        :options: is a dictionary of XML attributes to set within the <load-configuration> RPC.

        The :contents: are interpreted by the :options: as follows:

        format='text' and action='set', then :contents: is a string containing a series of "set" commands

        format='text', then :contents: is a string containing Junos configuration in curly-brace/text format

        <otherwise> :contents: is XML structure
        """
        rpc = E('load-configuration', options)

        if ('action' in options) and (options['action'] == 'set'):
            rpc.append(E('configuration-set', contents))
        elif ('format' in options) and (options['format'] == 'text'):
            rpc.append(E('configuration-text', contents))
        else:
            # otherwise, it's just XML Element
            if contents.tag != 'configuration':
                etree.SubElement(rpc, 'configuration').append(contents)
            else:
                rpc.append(contents)

        return self._junos.execute(rpc)

    # -----------------------------------------------------------------------
    # cli
    # -----------------------------------------------------------------------

    def cli(self, command, format='text'):
        rpc = E('command', command)
        if 'text' == format:
            rpc.attrib['format'] = 'text'
        rv = self._junos.execute(rpc)
        if format == 'dict':
            return self._lxmlparser(rv)
        else:
            return self._junos.execute(rpc)

    # -----------------------------------------------------------------------
    # method missing
    # -----------------------------------------------------------------------

    def __getattr__(self, rpc_cmd_name):
        """
          metaprograms a function to execute the :rpc_cmd_name:

          the caller will be passing (*vargs, **kvargs) on
          execution of the meta function; these are the specific
          rpc command arguments(**kvargs) and options bound
          as XML attributes (*vargs)
        """

        rpc_cmd = re.sub('_', '-', rpc_cmd_name)

        def _exec_rpc(*vargs, **kvargs):
            # create the rpc as XML command
            rpc = etree.Element(rpc_cmd)

            # kvargs are the command parameter/values
            if kvargs:
                for arg_name, arg_value in kvargs.items():
                    if arg_name not in ('dev_timeout', '_format'):
                        arg_name = re.sub('_', '-', arg_name)
                        if isinstance(arg_value, (tuple, list)):
                            for a in arg_value:
                                arg = etree.SubElement(rpc, arg_name)
                                if a is not True:
                                    arg.text = a
                        else:
                            arg = etree.SubElement(rpc, arg_name)
                            if arg_value is not True:
                                arg.text = arg_value

            # vargs[0] is a dict, command options like format='text'
            if vargs:
                for k, v in vargs[0].items():
                    if v is not True:
                        rpc.attrib[k] = v

            # now invoke the command against the
            # associated :junos: device and return
            # the results per :junos:execute()
            timeout = kvargs.get('dev_timeout')

            if timeout:
                rv = self._junos.execute(rpc, dev_timeout=timeout)
            else:
                rv = self._junos.execute(rpc)

            format = kvargs.get('_format', 'xml')
            if format == 'dict':
                return self._lxmlparser(rv)
            else:
                return rv

        # metabind help() and the function name to the :rpc_cmd_name:
        # provided by the caller ... that's about all we can do, yo!

        _exec_rpc.__doc__ = rpc_cmd
        _exec_rpc.__name__ = rpc_cmd_name

        # return the metafunction that the caller will in-turn invoke
        return _exec_rpc

    # -----------------------------------------------------------------------
    # callable
    # -----------------------------------------------------------------------

    def __call__(self, rpc_cmd, **kvargs):
        """
          callable will execute the provided :rpc_cmd: against the
          attached :junos: object and return the RPC response per
          :junos:execute()

          kvargs is simply passed 'as-is' to :junos:execute()
        """
        return self._junos.execute(rpc_cmd, **kvargs)
