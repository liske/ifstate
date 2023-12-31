---
title: defaults
layout: page
permalink: docs/defaults/
---

[Schema description](../../schema/#defaults)
 
```yaml
defaults:
  # list of defaults settings
  - match:
      # regex matching all interfaces
      - ifname: ''
    # remove any ip addresses if an interface has no `addresses:` setting
    clear_addresses: true
    # add some implicit link settings
    link:
      state: down
      ifalias: ''
```

With *defaults* it is possible to configure implicit default settings for interfaces. The `match:` option is a filter to select on which interfaces the defaults should be applied. Only the defaults of the first match are applied. There are several [*clear_...* settings](../schema/#defaults_items) which allows to clear interface settings (*addresses*, *fdb*, ...).

[Back](..#configuration-file)
