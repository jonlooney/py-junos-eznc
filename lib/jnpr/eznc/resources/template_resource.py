import pdb

# 3rd-party
from lxml import etree
from lxml.builder import E 

# package modules
from .. import jxml as JXML
from .resource import Resource, P_JUNOS_EXISTS, P_JUNOS_ACTIVE

class TemplateResource( Resource ):

  ### -------------------------------------------------------------------------
  ### read
  ### -------------------------------------------------------------------------

  def read(self):
    """
      read resource configuration from device
    """
    self.has.clear()
    self._has_xml = self._xml_config_read()

    # if the resource does not exist in Junos, then mark
    # the :has: accordingly and invoke :_init_has: for any
    # defaults

    if None == self._has_xml or not len(self._has_xml):
      for name in self._name:
        self.has[P_JUNOS_EXISTS+'_'+name] = False
        self.has[P_JUNOS_ACTIVE+'_'+name] = False
        self._init_has()
      return None

    # the xml_read_parser *MUST* be implement by the 
    # resource subclass.  it is used to parse the XML
    # into native python structures.

    self._xml_to_py( self._has_xml, self.has )

    # return the python structure represntation
    return self.has

  ### -------------------------------------------------------------------------
  ### activate
  ### -------------------------------------------------------------------------

  def activate(self):
    """
      write config to activate resource; i.e. "activate ..."
    """
    # no action needed if it's already active 
    if self.has[P_JUNOS_ACTIVE] == True: return False

    xml = self._xml_template_active( JXML.ACTIVATE )
    rsp = self._xml_config_write( xml )

    self.has[P_JUNOS_ACTIVE] = True
    return True

  ### -------------------------------------------------------------------------
  ### deactivate
  ### -------------------------------------------------------------------------

  def deactivate(self):
    """
      write config to deactivate resource, i.e. "deactivate ..."
    """
    # no action needed if it's already deactive
    if self.has[P_JUNOS_ACTIVE] == False: return False

    xml = self._xml_template_active( JXML.DEACTIVATE )
    rsp = self._xml_config_write( xml )

    self.has[P_JUNOS_ACTIVE] = False        
    return True

  ### -------------------------------------------------------------------------
  ### delete
  ### -------------------------------------------------------------------------

  def delete(self):
    """
      remove configuration from Junos device
    """
    # cannot delete something that doesn't exist

    if not self.exists: return False

    xml = self._xml_template_delete()
    rsp = self._xml_config_write( xml )

    # reset the :has: attribute
    self.has.clear()
    self.has[P_JUNOS_EXISTS] = False
    self.has[P_JUNOS_ACTIVE] = False

    return True

  ### -------------------------------------------------------------------------
  ### rename
  ### -------------------------------------------------------------------------

  def rename(self, new_name=None, **kvargs):
    """
      not supported (for now) - raise RuntimeError
    """
    raise RuntimeError("rename not supported on %s" % self.__class__.__name__)

  ### -------------------------------------------------------------------------
  ### reorder
  ### -------------------------------------------------------------------------

  def reorder( self, **kvargs ):
    """
      not supported - raises RuntimeError
    """
    raise RuntimeError("reorder not supported on %s" % self.__class__.__name__)

  ##### -----------------------------------------------------------------------
  ##### resource subclass helper methods
  ##### -----------------------------------------------------------------------

  def _xml_config_read(self):
    """
      read the resource config from the Junos device
    """
    return self._junos.rpc.get_config(self._xml_template_read())

  def _xml_template_read(self):
    t = self._j2_ldr.get_template(self._j2_rd+'.j2.xml' )    
    return etree.XML(t.render(self._name))    

  def _xml_template_names_only( self ):
    t = self._j2_ldr.get_template(self._j2_rd)
    return etree.XML(t.render(self._name, NAMES_ONLY=True))  

  def _xml_build_change(self):
    """
      run the templater to produce the XML for change
    """
    return self._xml_template_write()

  def _set_ea_status( self, xml_ele, to_py ):
    for name in self._xpath_names:
      if xml_ele[name] is not None:        
        to_py[P_JUNOS_EXISTS+'_'+name] = True 
        to_py[P_JUNOS_ACTIVE+'_'+name] = False if xml_ele[name].attrib.has_key('inactive') else True
      else:
        to_py[P_JUNOS_EXISTS+'_'+name] = False
        to_py[P_JUNOS_ACTIVE+'_'+name] = False

  ##### -----------------------------------------------------------------------
  ##### standard template resource methods
  ##### -----------------------------------------------------------------------

  def _xml_template_active(self, cmd):
    """
      used to activate/deactivate configuration based on :cmd:
    """
    xml = self._xml_template_names_only()
    for name,xpath in self._xpath_names.items():
      ele = xml.find(xpath)
      ele.attrib.update(cmd)
    return xml

  def _xml_template_delete(self):
    xml = self._xml_template_names_only()
    for name,xpath in self._xpath_names.items():
      ele = xml.find(xpath)
      ele.attrib.update( JXML.DEL )
    return xml