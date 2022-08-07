# Tasks
Each task sends info about the current operation being executed on a websocket.
A message sent on the websocket is a `WebsocketMessage` and have this definition:

```python
class WebsocketMessage(TypedDict):
    type: str  # message type: status, ...
    channel: str  # message identifier to distinguish between messages 
    payload: Any  # content of the message
```

The payload sent by the task are `StatusMessage`s, i.e. `WebsocketMessage`s where `type="status"` and the channel is the id of the Mod of this status belongs to.

A `StatusMessage`'s payload is a `ModStatus` object having this definition:

```python
class ModStatus(object):
    installed: ModRevision | bool  # revision currently installed
    downloaded: List[ModRevision] | bool  # list of revisions already downloaded
    starred: bool  # if this mod is starred
    playlists: List[dict]  # List of playlists where this mod is present
    installing: bool  # true if a install task currently active for this mod 
    operation: dict  # info about the current operation being executed by a task on this mod (install, uninstall, or update)
```

If there is an operation running on this mod the `operation` field of the `ModStatus` object 
contains the status of that operation. An `operation` object always have two fields:

```python
base = {
    "op": operation,  # the operation running (install, uninstall, update)  
    "state": state,  # a identifier of the current state of the operation
}
```

Optionally, the `operation` object could have a `mod` and a `revision` fields related to the Mod and the Revision to which this status refers.
For example, if `op="install"`, then `mod` and `revision` fields refers respectively to the Mod and the Revision to which the current operation refers.

If an error happens during the operation is running, then the `operation` have this form:
```python
error_state = {
    "op": operation,  # install, uninstall, update  
    "state": "error",
    "code": code, # identifier code of the error
    "message": message # a description about the error happened
}
```
Next sections summarize into tables the states and the error that each operation can assume during its execution

## install
An install `operation` object always have `op="install"` and represent a mod installing operation.

### states
This table summarizes the status that should be notified during an installation operation.  

| Identifier (`state` field)  | Description                                                                                                             | Other fields                                                                                                                                                                                                                                                                     |
|-----------------------------|-------------------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `get_mod_info`              | Info about the Mod and the Revision will be retrieved from the remote site and the database                             | /                                                                                                                                                                                                                                                                                |
| `get_dependencies`          | Info about the mod's dependencies (dependency tree) will be retrieved from the remote                                   | `mod`: the mod being installed whose dependency tree will be generated<br>`revision`: the revision being installed                                                                                                                                                               |
| `installing_dependency`     | The mod (dependency) specified in the `mod` field will be installed[^1]                                                 | `mod`: the dependency will be installed<br>`revision`: the dependency's revision will be installed                                                                                                                                                                               |
| `get_download_url`          | The download url of the revision in the `revision` field, will be generated from the remote                             | `mod`: the mod being installed<br>`revision`: the revision whose dowload url being generated                                                                                                                                                                                     |
| `wait_for_file`             | The task cannot download the `revision` automatically, so it will wait that the user manually donwload the zip file[^2] | `mod`: the mod being installed<br>`revision`: the revision being installed, whose download_url must be manually donwloaded into the `download_folder` path<br>`timeout`: seconds the task will wait before aborting<br>`download_folder`: path where the zip file must be placed |
| `downloading`               | The `revision` zip file is being downloaded                                                                             | `mod`: the mod being installed<br>`revision`: the revision being downloaded<br>`total_bytes`: (optional) the size (in bytes) of the zip file<br>`downloaded_bytes`: (optional) bytes already downloaded                                                                          |
| `unzip`                     | The zip file is being unzipped                                                                                          | `mod`: the mod being installed<br>`revision`: the revision being installed                                                                                                                                                                                                       |
| `copying`                   | The zip file content is being copied to the installation path                                                           | `mod`: the mod being installed<br>`revision`: the revision being installed<br>`total_bytes`: (optional) the total size (in bytes) to copy<br>`copied_bytes`: (optional) bytes already copied                                                                                     |
| `done`                      | Installation completed successfully                                                                                     | `mod`: the installed mod<br>`revsion` the installed revision                                                                                                                                                                                                                     |


[^1]: An application should now subscribe to the websocket channel `mod.id` to obtain status about the installation operation of the dependency.
[^2]: The download url can be obtained from the `revision.download_url` field

### errors
This table summarizes the errors that could be notified during an installation operation. 
An error `operation` object always have the field `state="error"`, and always have fields `code` and `message` that
describes the error happened. It could have other optional fields.

| `state` | `code`                  | `message`                                                                                                     | Description                                                                                                                                                                                                          | Other fields                                                                               |
|---------|-------------------------|---------------------------------------------------------------------------------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------|
| `error` | `no_path_configuration` | `CS folders location not found. Please check your configuration`                                              | The Cities Skylines installation and data folder have not been setted into the database                                                                                                                              | `mod`: the mod being installed                                                             |
| `error` | `revision_not_found`    | `Revision not found: {revision_id}`                                                                           | The revision requested (by its id) is not a mod's actual revision                                                                                                                                                    | `mod`: the mod being installed                                                             |
| `error` | `mod_already_installed` | `Another revision already installed: {mod.installed_revision_association.revision.name}`                      | another revision is already installed. Uninstall it before installing another revision.                                                                                                                              | `mod`: the mod being installed<br>`installed_revision`: the revision already installed[^1] |
| `error` | `timeout`               | `File download timeout`                                                                                       | The waiting for manual download of the zip file have reached the timeout                                                                                                                                             | `mod`: the mod being installed<br>`revision`: the revision being installed                 |
| `error` | `http_error`            | `Http error during get_download_url: {url}` / <br>`{http_message}`/<br>`Http error during downloading: {url}` | An http error happened during the `get_download_url` operation /<br>An http error happened during zip download. Its message is into the field `message` /<br>An http error happened before starting the zip download | `mod`: the mod being installed<br>`revision`: the revision being installed                 |
| `error` | `zip_error`             | `Zip file not found`                                                                                          | The zip file wasn't found at the zip file path                                                                                                                                                                       | `mod`: the mod being installed<br>`revision`: the revision being downloaded                |
| `error` | `exception`             | `{exception_msg}`                                                                                             | An exception have been raised during the operation, the exception string is into the field `message`                                                                                                                 | `mod`: the mod being installed<br>`revision`: the revision being installed                 |

[^1]: this value is also set into the field `installed` of the status object


## uninstall
An uninstall `operation` object always have `op="uninstall"` and represent a mod uninstalling operation.

### states
This table summarizes the status that should be notified during an uninstallation operation.  

| Identifier (`state` field)  | Description                                                         | Other fields |
|-----------------------------|---------------------------------------------------------------------|--------------|
| `get_mod_info`              | Info about the Mod to uninstall will be retrieved from the database | /            |
| `remove_folder`             | The Mod folder is being deleted from the installation folder        | /            |
| `done`                      | Installation completed successfully                                 | /            |

### errors
This table summarizes the errors that could be notified during an uninstallation operation.
An error `operation` object always have the field `state="error"`, and always have fields `code` and `message` that
describes the error happened. It could have other optional fields.

| `state` | `code`              | `message`                                 | Description                                                                                          | Other fields |
|---------|---------------------|-------------------------------------------|------------------------------------------------------------------------------------------------------|--------------|
| `error` | `mod_not_found`     | `Mod not found: {mod_id}`                 | The requested mod doesn't exists into the database                                                   | /            |
| `error` | `mod_not_installed` | `No installed revision for Mod: {mod_id}` | No revision of the mod seems to be installed                                                         | /            |
| `error` | `exception`         | `{exception_msg}`                         | An exception have been raised during the operation, the exception string is into the field `message` | /            |
