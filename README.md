# pylib Package

This is a py utils lib package, here are log and lots of methods.
All methods you can see in file methods.py.

# Usage
```python
from pylib.log import log
log.debug('msg')
log.info('msg')
log.warning('msg')
log.error('msg')
log.critical('msg')
log.log('DEBUG', 'msg')
log.log('INFO', 'msg')
log.log('WARNING', 'msg')
log.log('ERROR', 'msg')
log.log('CRITICAL', 'msg', silence=True)

from pylib.methods import Methods
Methods.get_stack_funcs()
data_desensitived = Methods.mask_sensitive_data(dict_data)
```
