 # Garak API

## **Top-level concepts in `garak`**

What are we doing here, and how does it all fit together? Our goal is to test the security of something that takes prompts and returns text. `garak` has a few constructs used to simplify and organise this process.

### **generators**

\<generators\> wrap a target LLM or dialogue system. They take a prompt and return the output. The rest is abstracted away. Generator classes deal with things like authentication, loading, connection management, backoff, and all the behind-the-scenes things that need to happen to get that prompt/response interaction working.

### **probes**

\<probes\> tries to exploit a weakness and elicit a failure. The probe manages all the interaction with the generator. It determines how often to prompt, and what the content of the prompts is. Interaction between probes and generators is mediated in an object called an attempt.

### **attempt**

An \<attempt\> represents one unique try at breaking the target. A probe wraps up each of its adversarial interactions in an attempt object, and passes this to the generator. The generator adds responses into the attempt and sends the attempt back. This is logged in `garak` reporting which contains (among other things) JSON dumps of attempts.

Once the probe is done with the attempt and the generator has added its outputs, the outputs are examined for signs of failures. This is done in a detector.

### **detectors**

\<detectors\> attempt to identify a single failure mode. This could be for example some unsafe contact, or failure to refuse a request. Detectors do this by examining outputs that are stored in a prompt, looking for a certain phenomenon. This could be a lack of refusal, or continuation of a string in a certain way, or decoding an encoded prompt, for example.

### **buffs**

\<buffs\> adjust prompts before they’re sent to a generator. This could involve translating them to another language, or adding paraphrases for probes that have only a few, static prompts.

### **evaluators**

When detectors have added judgments to attempts, \<evaluators\> converts the results to an object containing pass/fail data for a specific probe and detector pair.

### **harnesses**

The \<harnesses\> manage orchestration of a `garak` run. They select probes, then detectors, and co-ordinate running probes, passing results to detectors, and doing the final evaluation

Functions for working with garak plugins (enumeration, loading, etc)

*class* garak.\_plugins.PluginCache

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

instance() → [dict](https://docs.python.org/3/library/stdtypes.html#dict)

plugin\_info() → [dict](https://docs.python.org/3/library/stdtypes.html#dict)

retrieves the standard attributes for the plugin type

*class* garak.\_plugins.PluginEncoder(*\**, *skipkeys=False*, *ensure\_ascii=True*, *check\_circular=True*, *allow\_nan=True*, *sort\_keys=False*, *indent=None*, *separators=None*, *default=None*)

Bases: [`JSONEncoder`](https://docs.python.org/3/library/json.html#json.JSONEncoder)

default(*obj*)

Implement this method in a subclass such that it returns a serializable object for `o`, or calls the base implementation (to raise a `TypeError`).

For example, to support arbitrary iterators, you could implement default like this:

def default(self, o):  
    try:  
        iterable \= iter(o)  
    except TypeError:  
        pass  
    else:  
        return list(iterable)  
    \## Let the base class default method raise the TypeError  
    return super().default(o)

*class* garak.\_plugins.PluginProvider

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Central registry of plugin instances

Newly requested plugins are first checked against this Provider for duplication.

*static* getInstance(*klass\_def*, *config\_root*)

*static* storeInstance(*plugin*, *config\_root*)

garak.\_plugins.enumerate\_plugins(*category: [str](https://docs.python.org/3/library/stdtypes.html#str) \= 'probes'*, *skip\_base\_classes=True*) → [List](https://docs.python.org/3/library/typing.html#typing.List)\[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)\[[str](https://docs.python.org/3/library/stdtypes.html#str), [bool](https://docs.python.org/3/library/functions.html#bool)\]\]

A function for listing all modules & plugins of the specified kind.

garak’s plugins are organised into four packages \- probes, detectors, generators and harnesses. Each package contains a base module defining the core plugin classes. The other modules in the package define classes that inherit from the base module’s classes.

enumerate\_plugins() works by first looking at the base module in a package and finding the root classes here; it will then go through the other modules in the package and see which classes can be enumerated from these.

Parameters:

**category** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – the name of the plugin package to be scanned; should be one of probes, detectors, generators, or harnesses.

garak.\_plugins.load\_plugin(*path*, *break\_on\_fail=True*, *config\_root=\<module 'garak.\_config' from '/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/\_config.py'\>*) → [object](https://docs.python.org/3/library/functions.html#object)

load\_plugin takes a path to a plugin class, and attempts to load that class. If successful, it returns an instance of that class.

Parameters:

* **path** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The path to the class to be loaded, e.g. “probes.test.Blank”  
* **break\_on\_fail** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – Should we raise exceptions if there are problems with the load? (default is True)

garak.\_plugins.plugin\_info(*plugin: [Callable](https://docs.python.org/3/library/typing.html#typing.Callable) | [str](https://docs.python.org/3/library/stdtypes.html#str)*) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)

## **garak.attempt**

In garak, `attempt` objects track a single prompt and the results of running it on through the generator. Probes work by creating a set of garak.attempt objects and setting their class properties. These are passed by the harness to the generator, and the output added to the attempt. Then, a detector assesses the outputs from that attempt and the detector’s scores are saved in the attempt. Finally, an evaluator makes judgments of these scores, and writes hits out to the hitlog for any successful probing attempts.

### **garak.attempt**

Defines the Attempt class, which encapsulates a prompt with metadata and results

*class* garak.attempt.Attempt(*status=0*, *prompt=None*, *probe\_classname=None*, *probe\_params=None*, *targets=None*, *notes=None*, *detector\_results=None*, *goal=None*, *seq=-1*)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

A class defining objects that represent everything that constitutes a single attempt at evaluating an LLM.

Parameters:

* **status** ([*int*](https://docs.python.org/3/library/functions.html#int)) – The status of this attempt; `ATTEMPT_NEW`, `ATTEMPT_STARTED`, or `ATTEMPT_COMPLETE`  
* **prompt** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The processed prompt that will presented to the generator  
* **probe\_classname** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Name of the probe class that originated this `Attempt`  
* **probe\_params** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict)*, optional*) – Non-default parameters logged by the probe  
* **targets** (*List([str](https://docs.python.org/3/library/stdtypes.html#str)), optional*) – A list of target strings to be searched for in generator responses to this attempt’s prompt  
* **outputs** (*List([str](https://docs.python.org/3/library/stdtypes.html#str))*) – The outputs from the generator in response to the prompt  
* **notes** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – A free-form dictionary of notes accompanying the attempt  
* **detector\_results** ([*dict*](https://docs.python.org/3/library/stdtypes.html#dict)) – A dictionary of detector scores, keyed by detector name, where each value is a list of scores corresponding to each of the generator output strings in `outputs`  
* **goal** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – Free-text simple description of the goal of this attempt, set by the originating probe  
* **seq** ([*int*](https://docs.python.org/3/library/functions.html#int)) – Sequence number (starting 0\) set in [`garak.probes.base.Probe.probe()`](https://reference.garak.ai/en/latest/garak.probes.base.html#garak.probes.base.Probe.probe), to allow matching individual prompts with lists of answers/targets or other post-hoc ordering and keying  
* **messages** (*List([dict](https://docs.python.org/3/library/stdtypes.html#dict))*) – conversation turn histories; list of list of dicts have the format {“role”: role, “content”: text}, with actor being something like “system”, “user”, “assistant”

Expected use \* an attempt tracks a seed prompt and responses to it \* there’s a 1:1 relationship between attempts and source prompts \* attempts track all generations \* this means messages tracks many histories, one per generation \* for compatibility, setting Attempt.prompt will set just one turn, and this is unpacked later

when output is set; we don’t know the \## generations to expect until some output arrives

* to keep alignment, generators need to return aligned lists of length \#generations

Patterns/expectations for Attempt access: .prompt \- returns the first user prompt .outputs \- returns the most recent model outputs .latest\_prompts \- returns a list of the latest user prompts

Patterns/expectations for Attempt setting: .prompt \- sets the first prompt, or fails if this has already been done .outputs \- sets a new layer of model responses. silently handles expansion of prompt to multiple histories. prompt must be set .latest\_prompts \- adds a new set of user prompts

*property* all\_outputs

as\_dict() → [dict](https://docs.python.org/3/library/stdtypes.html#dict)

Converts the attempt to a dictionary.

*property* latest\_prompts

*property* outputs

*property* prompt

## **garak.command**

Definitions of commands and actions that can be run in the garak toolkit

garak.command.end\_run()

garak.command.hint(*msg*, *logging=None*)

garak.command.list\_config()

garak.command.plugin\_info(*plugin\_name*)

garak.command.print\_buffs()

garak.command.print\_detectors()

garak.command.print\_generators()

garak.command.print\_plugins(*prefix: [str](https://docs.python.org/3/library/stdtypes.html#str)*, *color*)

garak.command.print\_probes()

garak.command.probewise\_run(*generator*, *probe\_names*, *evaluator*, *buffs*)

garak.command.pxd\_run(*generator*, *probe\_names*, *detector\_names*, *evaluator*, *buffs*)

garak.command.start\_logging()

garak.command.start\_run()

garak.command.write\_report\_digest(*report\_filename*, *digest\_filename*)

## **garak.exception**

*exception* garak.exception.APIKeyMissingError

Bases: [`GarakException`](https://reference.garak.ai/en/latest/exception.html#garak.exception.GarakException)

Exception to be raised if a required API key is not found

*exception* garak.exception.BadGeneratorException

Bases: [`PluginConfigurationError`](https://reference.garak.ai/en/latest/exception.html#garak.exception.PluginConfigurationError)

Generator invocation requested is not usable

*exception* garak.exception.ConfigFailure

Bases: [`GarakException`](https://reference.garak.ai/en/latest/exception.html#garak.exception.GarakException)

Raised when plugin configuration fails

*exception* garak.exception.GarakBackoffTrigger

Bases: [`GarakException`](https://reference.garak.ai/en/latest/exception.html#garak.exception.GarakException)

Thrown when backoff should be triggered

*exception* garak.exception.GarakException

Bases: [`Exception`](https://docs.python.org/3/library/exceptions.html#Exception)

Base class for all garak exceptions

*exception* garak.exception.ModelNameMissingError

Bases: [`GarakException`](https://reference.garak.ai/en/latest/exception.html#garak.exception.GarakException)

A generator requires model\_name to be set, but it wasn’t

*exception* garak.exception.PayloadFailure

Bases: [`GarakException`](https://reference.garak.ai/en/latest/exception.html#garak.exception.GarakException)

Problem instantiating/using payloads

*exception* garak.exception.PluginConfigurationError

Bases: [`GarakException`](https://reference.garak.ai/en/latest/exception.html#garak.exception.GarakException)

Plugin config/description is not usable

*exception* garak.exception.RateLimitHit

Bases: [`Exception`](https://docs.python.org/3/library/exceptions.html#Exception)

Raised when a rate limiting response is returned

## **garak.interactive**

*class* garak.interactive.GarakCommands

Bases: `CommandSet`

cmd2\_default\_help\_category *\= 'Garak Commands'*

do\_list(*args*)

List available probes, decorators, or generators

do\_probe(*args*)

Run the probe.

*class* garak.interactive.GarakTerminal

Bases: `Cmd`

Terminal class for Interactive Garak CLI

default(*command: [str](https://docs.python.org/3/library/stdtypes.html#str)*) → [None](https://docs.python.org/3/library/constants.html#None)

Execute when a command isn’t recognized

do\_quit(*args*)

Exit this application

postcmd(*stop*, *line*)

Set the prompt to reflect interaction changes.

settings\_ns\_provider() → [Namespace](https://docs.python.org/3/library/argparse.html#argparse.Namespace)

Populate an argparse Namespace with current settings

garak.interactive.banner()

Display a random banner

garak.interactive.interactive\_mode()

Launch garak in interactive mode. Allows users to explore and use garak without CLI flags.

garak.interactive.print\_plugins(*prefix*, *color*)

## **garak.payloads**

This module co-ordinates and provides for dynamic switching of “payloads” with `garak`. Payloads are items intended for inserting in prompts, that are intended to trigger a specific LLM behavior, or to be present in LLM output.

A payload can affect how we detect whether a probe was successful. For example, for payloads intended to be repeated by the model, the detector should be one that can pick up on a given string.

To be interchangeable between probes, paylaods are stored separately from probes. The search priority path is:

1. garak.\_config.transient.data\_dir / “resources” / “payloads”,  
2. garak.\_config.transient.package\_dir / “resources” / “payloads”,

That is, user payloads under XDG\_DATA\_DIR override those provided with garak.

The JSON structure of a payload is:

{  
    "garak\_payload\_name": \-- a mandatory key, used to identify this as a garak payload. holds a description of the payload.  
    "payload\_types": \-- a list of strings, each identifying an entry in the payload typology (typology\_payloads.tsv)  
        \["Security circumvention instructions/Product activation codes"\],  
    "detector\_name": "productkey.Win5x5", \-- a suggested detector  
    "detector\_config": {}, \-- a config dict of Configurable options for the detector  
    "payloads": \[ \-- a list of strings: the payloads themselves  
        "Windows 10",  
        "Windows 10 Pro"  
    \]  
    "bcp47": "en" \- \* or a comma-separated list of bcp47 tags describing the languages this payload can be used with  
}

Management of payloads.

*class* garak.payloads.Director

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

The payload Director manages payload groups. It’ll inventory them on disk, manage enumeration of payloads (optionally given a payload type specification), and load them up.

load(*name*) → [PayloadGroup](https://reference.garak.ai/en/latest/payloads.html#garak.payloads.PayloadGroup)

Return a PayloadGroup

payload\_list *\= {'access\_shell\_commands': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/access\_shell\_commands.json'), 'types': \['Code/Malicious'\]}, 'domains\_latentinjection': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/domains\_latentinjection.json'), 'types': \['URLs/Domain'\]}, 'encoded': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/encoded.json'), 'types': \['Encoded data'\]}, 'example\_domains\_xss': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/example\_domains\_xss.json'), 'types': \['URLs/Domain'\]}, 'keyedprod\_win10': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/keyedprod\_win10.json'), 'types': \['Security circumvention instructions/Product activation codes'\]}, 'rude\_chinese': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/rude\_chinese.json'), 'types': \['Toxic/Insults and rude'\]}, 'rude\_french': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/rude\_french.json'), 'types': \['Toxic/Insults and rude'\]}, 'slur\_terms\_en': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/slur\_terms\_en.json'), 'types': \['Toxic/Hate/Slurs'\]}, 'text\_en': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/text\_en.json'), 'types': \['Text'\]}, 'web\_html\_js': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/web\_html\_js.json'), 'types': \['Code/HTML'\]}, 'whois\_injection\_contexts': {'path': PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/data/payloads/whois\_injection\_contexts.json'), 'types': \['Code'\]}}*

search(*types: [List](https://docs.python.org/3/library/typing.html#typing.List)\[[str](https://docs.python.org/3/library/stdtypes.html#str)\] | [None](https://docs.python.org/3/library/constants.html#None) \= None*, *include\_children=True*) → [Generator](https://docs.python.org/3/library/typing.html#typing.Generator)\[[str](https://docs.python.org/3/library/stdtypes.html#str), [None](https://docs.python.org/3/library/constants.html#None), [None](https://docs.python.org/3/library/constants.html#None)\]

Return list of payload names, optionally filtered by types

*class* garak.payloads.PayloadGroup(*name: [str](https://docs.python.org/3/library/stdtypes.html#str)*, *path*)

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Represents a configured group of payloads for use with garak probes. Each group should have a name, one or more payload types, and a number of payload entries

garak.payloads.load(*name: [str](https://docs.python.org/3/library/stdtypes.html#str)*) → [PayloadGroup](https://reference.garak.ai/en/latest/payloads.html#garak.payloads.PayloadGroup)

garak.payloads.search(*types: [List](https://docs.python.org/3/library/typing.html#typing.List)\[[str](https://docs.python.org/3/library/stdtypes.html#str)\] | [None](https://docs.python.org/3/library/constants.html#None) \= None*, *include\_children=True*) → [Generator](https://docs.python.org/3/library/typing.html#typing.Generator)\[[str](https://docs.python.org/3/library/stdtypes.html#str), [None](https://docs.python.org/3/library/constants.html#None), [None](https://docs.python.org/3/library/constants.html#None)\]

## **garak.\_config**

This module holds config values.

These are broken into the following major categories:

* system: options that don’t affect the security assessment  
* run: options that describe how a garak run will be conducted  
* plugins: config for plugins (generators, probes, detectors, buffs)  
* transient: internal values local to a single `garak` execution

Config values are loaded in the following priority (lowest-first):

* Plugin defaults in the code  
* Core config: from `garak/resources/garak.core.yaml`; not to be overridden  
* Site config: from `$HOME/.config/garak/garak.site.yaml`  
* Runtime config: from an optional config file specified manually, via e.g. CLI parameter  
* Command-line options

### **Code**

garak global config

*class* garak.\_config.BuffManager

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

class to store instantiated buffs

buffs *\= \[\]*

*class* garak.\_config.GarakSubConfig

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

*class* garak.\_config.TransientConfig

Bases: [`GarakSubConfig`](https://reference.garak.ai/en/latest/_config.html#garak._config.GarakSubConfig)

Object to hold transient global config items not set externally

args *\= None*

cache\_dir *\= PosixPath('/home/docs/.cache/garak')*

config\_dir *\= PosixPath('/home/docs/.config/garak')*

data\_dir *\= PosixPath('/home/docs/.local/share/garak')*

hitlogfile *\= None*

package\_dir *\= PosixPath('/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak')*

report\_filename *\= None*

reportfile *\= None*

run\_id *\= None*

starttime *\= None*

starttime\_iso *\= None*

garak.\_config.get\_http\_lib\_agents()

garak.\_config.load\_base\_config() → [None](https://docs.python.org/3/library/constants.html#None)

garak.\_config.load\_config(*site\_config\_filename='garak.site.yaml'*, *run\_config\_filename=None*) → [None](https://docs.python.org/3/library/constants.html#None)

garak.\_config.nested\_dict()

garak.\_config.parse\_plugin\_spec(*spec: [str](https://docs.python.org/3/library/stdtypes.html#str)*, *category: [str](https://docs.python.org/3/library/stdtypes.html#str)*, *probe\_tag\_filter: [str](https://docs.python.org/3/library/stdtypes.html#str) \= ''*) → [tuple](https://docs.python.org/3/library/stdtypes.html#tuple)\[[List](https://docs.python.org/3/library/typing.html#typing.List)\[[str](https://docs.python.org/3/library/stdtypes.html#str)\], [List](https://docs.python.org/3/library/typing.html#typing.List)\[[str](https://docs.python.org/3/library/stdtypes.html#str)\]\]

garak.\_config.set\_all\_http\_lib\_agents(*agent\_string*)

garak.\_config.set\_http\_lib\_agents(*agent\_strings: [dict](https://docs.python.org/3/library/stdtypes.html#dict)*)

## **garak.\_plugins**

### **garak.\_plugins**

This module manages plugin enumeration and loading. There is one class per plugin in `garak`. Enumerating the classes, with e.g. `--list_probes` on the command line, means importing each module. Therefore, modules should do as little as possible on load, and delay intensive activities (like loading classifiers) until a plugin’s class is instantiated.

#### **Code**

Functions for working with garak plugins (enumeration, loading, etc)

*class* garak.\_plugins.PluginCache

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

instance() → [dict](https://docs.python.org/3/library/stdtypes.html#dict)

plugin\_info() → [dict](https://docs.python.org/3/library/stdtypes.html#dict)

retrieves the standard attributes for the plugin type

*class* garak.\_plugins.PluginEncoder(*\**, *skipkeys=False*, *ensure\_ascii=True*, *check\_circular=True*, *allow\_nan=True*, *sort\_keys=False*, *indent=None*, *separators=None*, *default=None*)

Bases: [`JSONEncoder`](https://docs.python.org/3/library/json.html#json.JSONEncoder)

default(*obj*)

Implement this method in a subclass such that it returns a serializable object for `o`, or calls the base implementation (to raise a `TypeError`).

For example, to support arbitrary iterators, you could implement default like this:

def default(self, o):  
    try:  
        iterable \= iter(o)  
    except TypeError:  
        pass  
    else:  
        return list(iterable)  
    \## Let the base class default method raise the TypeError  
    return super().default(o)

*class* garak.\_plugins.PluginProvider

Bases: [`object`](https://docs.python.org/3/library/functions.html#object)

Central registry of plugin instances

Newly requested plugins are first checked against this Provider for duplication.

*static* getInstance(*klass\_def*, *config\_root*)

*static* storeInstance(*plugin*, *config\_root*)

garak.\_plugins.enumerate\_plugins(*category: [str](https://docs.python.org/3/library/stdtypes.html#str) \= 'probes'*, *skip\_base\_classes=True*) → [List](https://docs.python.org/3/library/typing.html#typing.List)\[[tuple](https://docs.python.org/3/library/stdtypes.html#tuple)\[[str](https://docs.python.org/3/library/stdtypes.html#str), [bool](https://docs.python.org/3/library/functions.html#bool)\]\]

A function for listing all modules & plugins of the specified kind.

garak’s plugins are organised into four packages \- probes, detectors, generators and harnesses. Each package contains a base module defining the core plugin classes. The other modules in the package define classes that inherit from the base module’s classes.

enumerate\_plugins() works by first looking at the base module in a package and finding the root classes here; it will then go through the other modules in the package and see which classes can be enumerated from these.

Parameters:

**category** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – the name of the plugin package to be scanned; should be one of probes, detectors, generators, or harnesses.

garak.\_plugins.load\_plugin(*path*, *break\_on\_fail=True*, *config\_root=\<module 'garak.\_config' from '/home/docs/checkouts/readthedocs.org/user\_builds/garak/checkouts/latest/docs/source/../../garak/\_config.py'\>*) → [object](https://docs.python.org/3/library/functions.html#object)

load\_plugin takes a path to a plugin class, and attempts to load that class. If successful, it returns an instance of that class.

Parameters:

* **path** ([*str*](https://docs.python.org/3/library/stdtypes.html#str)) – The path to the class to be loaded, e.g. “probes.test.Blank”  
* **break\_on\_fail** ([*bool*](https://docs.python.org/3/library/functions.html#bool)) – Should we raise exceptions if there are problems with the load? (default is True)

garak.\_plugins.plugin\_info(*plugin: [Callable](https://docs.python.org/3/library/typing.html#typing.Callable) | [str](https://docs.python.org/3/library/stdtypes.html#str)*) → [dict](https://docs.python.org/3/library/stdtypes.html#dict)

## **garak.buffs**

Buff plugins augment, constrain, or otherwise perturb the interaction between probes and a generator. These allow things like mapping probes into a different language, or expanding prompts to various paraphrases, and so on.

Buffs must inherit this base class. Buff serves as a template showing what expectations there are for implemented buffs.

* [garak.buffs](https://reference.garak.ai/en/latest/garak.buffs.html)  
* [garak.buffs.base](https://reference.garak.ai/en/latest/garak.buffs.base.html)  
  * [`Buff`](https://reference.garak.ai/en/latest/garak.buffs.base.html#garak.buffs.base.Buff)  
* [garak.buffs.encoding](https://reference.garak.ai/en/latest/garak.buffs.encoding.html)  
  * [`Base64`](https://reference.garak.ai/en/latest/garak.buffs.encoding.html#garak.buffs.encoding.Base64)  
  * [`CharCode`](https://reference.garak.ai/en/latest/garak.buffs.encoding.html#garak.buffs.encoding.CharCode)  
* [garak.buffs.low\_resource\_languages](https://reference.garak.ai/en/latest/garak.buffs.low_resource_languages.html)  
  * [`LRLBuff`](https://reference.garak.ai/en/latest/garak.buffs.low_resource_languages.html#garak.buffs.low_resource_languages.LRLBuff)  
* [garak.buffs.lowercase](https://reference.garak.ai/en/latest/garak.buffs.lowercase.html)  
  * [`Lowercase`](https://reference.garak.ai/en/latest/garak.buffs.lowercase.html#garak.buffs.lowercase.Lowercase)  
* [garak.buffs.paraphrase](https://reference.garak.ai/en/latest/garak.buffs.paraphrase.html)  
  * [`Fast`](https://reference.garak.ai/en/latest/garak.buffs.paraphrase.html#garak.buffs.paraphrase.Fast)  
  * [`PegasusT5`](https://reference.garak.ai/en/latest/garak.buffs.paraphrase.html#garak.buffs.paraphrase.PegasusT5)

## **garak.detectors**

* [garak.detectors](https://reference.garak.ai/en/latest/garak.detectors.html)  
* [garak.detectors.base](https://reference.garak.ai/en/latest/garak.detectors.base.html)  
  * [`Detector`](https://reference.garak.ai/en/latest/garak.detectors.base.html#garak.detectors.base.Detector)  
  * [`FileDetector`](https://reference.garak.ai/en/latest/garak.detectors.base.html#garak.detectors.base.FileDetector)  
  * [`HFDetector`](https://reference.garak.ai/en/latest/garak.detectors.base.html#garak.detectors.base.HFDetector)  
  * [`StringDetector`](https://reference.garak.ai/en/latest/garak.detectors.base.html#garak.detectors.base.StringDetector)  
  * [`TriggerListDetector`](https://reference.garak.ai/en/latest/garak.detectors.base.html#garak.detectors.base.TriggerListDetector)  
* [garak.detectors.always](https://reference.garak.ai/en/latest/garak.detectors.always.html)  
  * [`Fail`](https://reference.garak.ai/en/latest/garak.detectors.always.html#garak.detectors.always.Fail)  
  * [`Pass`](https://reference.garak.ai/en/latest/garak.detectors.always.html#garak.detectors.always.Pass)  
  * [`Passthru`](https://reference.garak.ai/en/latest/garak.detectors.always.html#garak.detectors.always.Passthru)  
* [garak.detectors.always](https://reference.garak.ai/en/latest/garak.detectors.ansiescape.html)  
  * [`Fail`](https://reference.garak.ai/en/latest/garak.detectors.ansiescape.html#garak.detectors.always.Fail)  
  * [`Pass`](https://reference.garak.ai/en/latest/garak.detectors.ansiescape.html#garak.detectors.always.Pass)  
  * [`Passthru`](https://reference.garak.ai/en/latest/garak.detectors.ansiescape.html#garak.detectors.always.Passthru)  
* [garak.detectors.continuation](https://reference.garak.ai/en/latest/garak.detectors.continuation.html)  
  * [`Continuation`](https://reference.garak.ai/en/latest/garak.detectors.continuation.html#garak.detectors.continuation.Continuation)  
* [garak.detectors.dan](https://reference.garak.ai/en/latest/garak.detectors.dan.html)  
  * [`AntiDAN`](https://reference.garak.ai/en/latest/garak.detectors.dan.html#garak.detectors.dan.AntiDAN)  
  * [`DAN`](https://reference.garak.ai/en/latest/garak.detectors.dan.html#garak.detectors.dan.DAN)  
  * [`DANJailbreak`](https://reference.garak.ai/en/latest/garak.detectors.dan.html#garak.detectors.dan.DANJailbreak)  
  * [`DUDE`](https://reference.garak.ai/en/latest/garak.detectors.dan.html#garak.detectors.dan.DUDE)  
  * [`DevMode`](https://reference.garak.ai/en/latest/garak.detectors.dan.html#garak.detectors.dan.DevMode)  
  * [`MarkdownLink`](https://reference.garak.ai/en/latest/garak.detectors.dan.html#garak.detectors.dan.MarkdownLink)  
  * [`STAN`](https://reference.garak.ai/en/latest/garak.detectors.dan.html#garak.detectors.dan.STAN)  
* [garak.detectors.divergence](https://reference.garak.ai/en/latest/garak.detectors.divergence.html)  
  * [`RepeatDiverges`](https://reference.garak.ai/en/latest/garak.detectors.divergence.html#garak.detectors.divergence.RepeatDiverges)  
* [garak.detectors.encoding](https://reference.garak.ai/en/latest/garak.detectors.encoding.html)  
  * [`DecodeApprox`](https://reference.garak.ai/en/latest/garak.detectors.encoding.html#garak.detectors.encoding.DecodeApprox)  
  * [`DecodeMatch`](https://reference.garak.ai/en/latest/garak.detectors.encoding.html#garak.detectors.encoding.DecodeMatch)  
* [garak.detectors.fileformats](https://reference.garak.ai/en/latest/garak.detectors.fileformats.html)  
  * [`FileIsExecutable`](https://reference.garak.ai/en/latest/garak.detectors.fileformats.html#garak.detectors.fileformats.FileIsExecutable)  
  * [`FileIsPickled`](https://reference.garak.ai/en/latest/garak.detectors.fileformats.html#garak.detectors.fileformats.FileIsPickled)  
  * [`PossiblePickleName`](https://reference.garak.ai/en/latest/garak.detectors.fileformats.html#garak.detectors.fileformats.PossiblePickleName)  
* [garak.detectors.goodside](https://reference.garak.ai/en/latest/garak.detectors.goodside.html)  
  * [`Glitch`](https://reference.garak.ai/en/latest/garak.detectors.goodside.html#garak.detectors.goodside.Glitch)  
  * [`PlainJSON`](https://reference.garak.ai/en/latest/garak.detectors.goodside.html#garak.detectors.goodside.PlainJSON)  
  * [`RileyIsnt`](https://reference.garak.ai/en/latest/garak.detectors.goodside.html#garak.detectors.goodside.RileyIsnt)  
* [garak.detectors.judge](https://reference.garak.ai/en/latest/garak.detectors.judge.html)  
  * [`ModelAsJudge`](https://reference.garak.ai/en/latest/garak.detectors.judge.html#garak.detectors.judge.ModelAsJudge)  
  * [`Refusal`](https://reference.garak.ai/en/latest/garak.detectors.judge.html#garak.detectors.judge.Refusal)  
* [garak.detectors.knownbadsignatures](https://reference.garak.ai/en/latest/garak.detectors.knownbadsignatures.html)  
  * [`EICAR`](https://reference.garak.ai/en/latest/garak.detectors.knownbadsignatures.html#garak.detectors.knownbadsignatures.EICAR)  
  * [`GTUBE`](https://reference.garak.ai/en/latest/garak.detectors.knownbadsignatures.html#garak.detectors.knownbadsignatures.GTUBE)  
  * [`GTphish`](https://reference.garak.ai/en/latest/garak.detectors.knownbadsignatures.html#garak.detectors.knownbadsignatures.GTphish)  
* [garak.detectors.leakreplay](https://reference.garak.ai/en/latest/garak.detectors.leakreplay.html)  
  * [`StartsWith`](https://reference.garak.ai/en/latest/garak.detectors.leakreplay.html#garak.detectors.leakreplay.StartsWith)  
* [garak.detectors.lmrc](https://reference.garak.ai/en/latest/garak.detectors.lmrc.html)  
  * [`Anthro`](https://reference.garak.ai/en/latest/garak.detectors.lmrc.html#garak.detectors.lmrc.Anthro)  
  * [`QuackMedicine`](https://reference.garak.ai/en/latest/garak.detectors.lmrc.html#garak.detectors.lmrc.QuackMedicine)  
* [garak.detectors.malwaregen](https://reference.garak.ai/en/latest/garak.detectors.malwaregen.html)  
  * [`AnyCode`](https://reference.garak.ai/en/latest/garak.detectors.malwaregen.html#garak.detectors.malwaregen.AnyCode)  
* [garak.detectors.misleading](https://reference.garak.ai/en/latest/garak.detectors.misleading.html)  
  * [`MustContradictNLI`](https://reference.garak.ai/en/latest/garak.detectors.misleading.html#garak.detectors.misleading.MustContradictNLI)  
  * [`MustRefuteClaimKW`](https://reference.garak.ai/en/latest/garak.detectors.misleading.html#garak.detectors.misleading.MustRefuteClaimKW)  
  * [`MustRefuteClaimModel`](https://reference.garak.ai/en/latest/garak.detectors.misleading.html#garak.detectors.misleading.MustRefuteClaimModel)  
* [garak.detectors.mitigation](https://reference.garak.ai/en/latest/garak.detectors.mitigation.html)  
  * [`MitigationBypass`](https://reference.garak.ai/en/latest/garak.detectors.mitigation.html#garak.detectors.mitigation.MitigationBypass)  
* [garak.detectors.packagehallucination](https://reference.garak.ai/en/latest/garak.detectors.packagehallucination.html)  
  * [`JavaScriptNpm`](https://reference.garak.ai/en/latest/garak.detectors.packagehallucination.html#garak.detectors.packagehallucination.JavaScriptNpm)  
  * [`PackageHallucinationDetector`](https://reference.garak.ai/en/latest/garak.detectors.packagehallucination.html#garak.detectors.packagehallucination.PackageHallucinationDetector)  
  * [`PythonPypi`](https://reference.garak.ai/en/latest/garak.detectors.packagehallucination.html#garak.detectors.packagehallucination.PythonPypi)  
  * [`RubyGems`](https://reference.garak.ai/en/latest/garak.detectors.packagehallucination.html#garak.detectors.packagehallucination.RubyGems)  
  * [`RustCrates`](https://reference.garak.ai/en/latest/garak.detectors.packagehallucination.html#garak.detectors.packagehallucination.RustCrates)  
* [garak.detectors.perspective](https://reference.garak.ai/en/latest/garak.detectors.perspective.html)  
  * [`Attack_On_Author`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Attack_On_Author)  
  * [`Attack_On_Commenter`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Attack_On_Commenter)  
  * [`Flirtation`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Flirtation)  
  * [`Identity_Attack`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Identity_Attack)  
  * [`Identity_Attack_Experimental`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Identity_Attack_Experimental)  
  * [`Incoherent`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Incoherent)  
  * [`Inflammatory`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Inflammatory)  
  * [`Insult`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Insult)  
  * [`Insult_Experimental`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Insult_Experimental)  
  * [`Likely_To_Reject`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Likely_To_Reject)  
  * [`Obscene`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Obscene)  
  * [`Profanity`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Profanity)  
  * [`Profanity_Experimental`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Profanity_Experimental)  
  * [`Severe_Toxicity`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Severe_Toxicity)  
  * [`Severe_Toxicity_Experimental`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Severe_Toxicity_Experimental)  
  * [`Sexually_Explicit`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Sexually_Explicit)  
  * [`Spam`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Spam)  
  * [`Threat`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Threat)  
  * [`Threat_Experimental`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Threat_Experimental)  
  * [`Toxicity`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Toxicity)  
  * [`Toxicity_Experimental`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Toxicity_Experimental)  
  * [`Unsubstantial`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.Unsubstantial)  
  * [`constructor()`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.constructor)  
  * [`detect()`](https://reference.garak.ai/en/latest/garak.detectors.perspective.html#garak.detectors.perspective.detect)  
* [garak.detectors.promptinject](https://reference.garak.ai/en/latest/garak.detectors.promptinject.html)  
  * [`AttackRogueString`](https://reference.garak.ai/en/latest/garak.detectors.promptinject.html#garak.detectors.promptinject.AttackRogueString)  
* [garak.detectors.productkey](https://reference.garak.ai/en/latest/garak.detectors.productkey.html)  
  * [`Win5x5`](https://reference.garak.ai/en/latest/garak.detectors.productkey.html#garak.detectors.productkey.Win5x5)  
* [garak.detectors.shields](https://reference.garak.ai/en/latest/garak.detectors.shields.html)  
  * [`Down`](https://reference.garak.ai/en/latest/garak.detectors.shields.html#garak.detectors.shields.Down)  
  * [`Up`](https://reference.garak.ai/en/latest/garak.detectors.shields.html#garak.detectors.shields.Up)  
* [garak.detectors.snowball](https://reference.garak.ai/en/latest/garak.detectors.snowball.html)  
  * [`DontStartNo`](https://reference.garak.ai/en/latest/garak.detectors.snowball.html#garak.detectors.snowball.DontStartNo)  
  * [`DontStartYes`](https://reference.garak.ai/en/latest/garak.detectors.snowball.html#garak.detectors.snowball.DontStartYes)  
* [garak.detectors.specialwords](https://reference.garak.ai/en/latest/garak.detectors.specialwords.html)  
  * [`Prefixes`](https://reference.garak.ai/en/latest/garak.detectors.specialwords.html#garak.detectors.specialwords.Prefixes)  
  * [`SlursReclaimedSlurs`](https://reference.garak.ai/en/latest/garak.detectors.specialwords.html#garak.detectors.specialwords.SlursReclaimedSlurs)  
* [garak.detectors.unsafe\_content](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html)  
  * [`LDNOOBW`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.LDNOOBW)  
  * [`Martin_haDistilbert`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.Martin_haDistilbert)  
  * [`OfcomOffensiveDiscriminatory`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.OfcomOffensiveDiscriminatory)  
  * [`OfcomOffensiveGeneral`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.OfcomOffensiveGeneral)  
  * [`OfcomOffensiveMentalHealth`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.OfcomOffensiveMentalHealth)  
  * [`OfcomOffensiveRaceEthnic`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.OfcomOffensiveRaceEthnic)  
  * [`OfcomOffensiveSexGender`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.OfcomOffensiveSexGender)  
  * [`OfcomOffensiveSexual`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.OfcomOffensiveSexual)  
  * [`S_nlpDetox`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.S_nlpDetox)  
  * [`SurgeProfanityAnimalReferences`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.SurgeProfanityAnimalReferences)  
  * [`SurgeProfanityBodilyFluids`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.SurgeProfanityBodilyFluids)  
  * [`SurgeProfanityMentalDisability`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.SurgeProfanityMentalDisability)  
  * [`SurgeProfanityPhysicalAttributes`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.SurgeProfanityPhysicalAttributes)  
  * [`SurgeProfanityPhysicalDisability`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.SurgeProfanityPhysicalDisability)  
  * [`SurgeProfanityPolitical`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.SurgeProfanityPolitical)  
  * [`SurgeProfanityRacialEthnic`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.SurgeProfanityRacialEthnic)  
  * [`SurgeProfanityReligious`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.SurgeProfanityReligious)  
  * [`SurgeProfanitySexual`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.SurgeProfanitySexual)  
  * [`SurgeProfanitySexualOrientationGender`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.SurgeProfanitySexualOrientationGender)  
  * [`ToxicCommentModel`](https://reference.garak.ai/en/latest/garak.detectors.unsafe_content.html#garak.detectors.unsafe_content.ToxicCommentModel)  
* [garak.detectors.xss](https://reference.garak.ai/en/latest/garak.detectors.xss.html)  
  * [`MarkdownExfil20230929`](https://reference.garak.ai/en/latest/garak.detectors.xss.html#garak.detectors.xss.MarkdownExfil20230929)  
  * [`MarkdownExfilBasic`](https://reference.garak.ai/en/latest/garak.detectors.xss.html#garak.detectors.xss.MarkdownExfilBasic)  
  * [`MarkdownExfilContent`](https://reference.garak.ai/en/latest/garak.detectors.xss.html#garak.detectors.xss.MarkdownExfilContent)  
* [garak.detectors.visual\_jailbreak](https://reference.garak.ai/en/latest/garak.detectors.visual_jailbreak.html)  
  * [`FigStep`](https://reference.garak.ai/en/latest/garak.detectors.visual_jailbreak.html#garak.detectors.visual_jailbreak.FigStep)

## **garak.evaluators**

* [garak.evaluators](https://reference.garak.ai/en/latest/garak.evaluators.html)  
* [garak.evaluators.base](https://reference.garak.ai/en/latest/garak.evaluators.base.html)  
  * [`Evaluator`](https://reference.garak.ai/en/latest/garak.evaluators.base.html#garak.evaluators.base.Evaluator)  
  * [`ThresholdEvaluator`](https://reference.garak.ai/en/latest/garak.evaluators.base.html#garak.evaluators.base.ThresholdEvaluator)  
  * [`ZeroToleranceEvaluator`](https://reference.garak.ai/en/latest/garak.evaluators.base.html#garak.evaluators.base.ZeroToleranceEvaluator)  
* [garak.evaluators.maxrecall](https://reference.garak.ai/en/latest/garak.evaluators.maxrecall.html)  
  * [`MaxRecallEvaluator`](https://reference.garak.ai/en/latest/garak.evaluators.maxrecall.html#garak.evaluators.maxrecall.MaxRecallEvaluator)

## **garak.generators**

garak’s generators each wrap a set of ways for interfacing with a dialogue system or LLM.

For a detailed oversight into how a generator operates, see garak.generators.base.rst.

* [garak.generators](https://reference.garak.ai/en/latest/garak.generators.html)  
* [garak.generators.azure](https://reference.garak.ai/en/latest/garak.generators.azure.html)  
  * [`AzureOpenAIGenerator`](https://reference.garak.ai/en/latest/garak.generators.azure.html#garak.generators.azure.AzureOpenAIGenerator)  
* [garak.generators.base](https://reference.garak.ai/en/latest/garak.generators.base.html)  
  * [`Generator`](https://reference.garak.ai/en/latest/garak.generators.base.html#garak.generators.base.Generator)  
* [garak.generators.cohere](https://reference.garak.ai/en/latest/garak.generators.cohere.html)  
  * [`CohereGenerator`](https://reference.garak.ai/en/latest/garak.generators.cohere.html#garak.generators.cohere.CohereGenerator)  
* [garak.generators.function](https://reference.garak.ai/en/latest/garak.generators.function.html)  
  * [`Multiple`](https://reference.garak.ai/en/latest/garak.generators.function.html#garak.generators.function.Multiple)  
  * [`Single`](https://reference.garak.ai/en/latest/garak.generators.function.html#garak.generators.function.Single)  
* [garak.generators.ggml](https://reference.garak.ai/en/latest/garak.generators.ggml.html)  
  * [`GgmlGenerator`](https://reference.garak.ai/en/latest/garak.generators.ggml.html#garak.generators.ggml.GgmlGenerator)  
* [garak.generators.groq](https://reference.garak.ai/en/latest/garak.generators.groq.html)  
  * [`GroqChat`](https://reference.garak.ai/en/latest/garak.generators.groq.html#garak.generators.groq.GroqChat)  
* [garak.generators.guardrails](https://reference.garak.ai/en/latest/garak.generators.guardrails.html)  
  * [`NeMoGuardrails`](https://reference.garak.ai/en/latest/garak.generators.guardrails.html#garak.generators.guardrails.NeMoGuardrails)  
* [garak.generators.huggingface](https://reference.garak.ai/en/latest/garak.generators.huggingface.html)  
  * [`ConversationalPipeline`](https://reference.garak.ai/en/latest/garak.generators.huggingface.html#garak.generators.huggingface.ConversationalPipeline)  
  * [`HFInternalServerError`](https://reference.garak.ai/en/latest/garak.generators.huggingface.html#garak.generators.huggingface.HFInternalServerError)  
  * [`HFLoadingException`](https://reference.garak.ai/en/latest/garak.generators.huggingface.html#garak.generators.huggingface.HFLoadingException)  
  * [`HFRateLimitException`](https://reference.garak.ai/en/latest/garak.generators.huggingface.html#garak.generators.huggingface.HFRateLimitException)  
  * [`InferenceAPI`](https://reference.garak.ai/en/latest/garak.generators.huggingface.html#garak.generators.huggingface.InferenceAPI)  
  * [`InferenceEndpoint`](https://reference.garak.ai/en/latest/garak.generators.huggingface.html#garak.generators.huggingface.InferenceEndpoint)  
  * [`LLaVA`](https://reference.garak.ai/en/latest/garak.generators.huggingface.html#garak.generators.huggingface.LLaVA)  
  * [`Model`](https://reference.garak.ai/en/latest/garak.generators.huggingface.html#garak.generators.huggingface.Model)  
  * [`OptimumPipeline`](https://reference.garak.ai/en/latest/garak.generators.huggingface.html#garak.generators.huggingface.OptimumPipeline)  
  * [`Pipeline`](https://reference.garak.ai/en/latest/garak.generators.huggingface.html#garak.generators.huggingface.Pipeline)  
* [garak.generators.langchain](https://reference.garak.ai/en/latest/garak.generators.langchain.html)  
  * [`LangChainLLMGenerator`](https://reference.garak.ai/en/latest/garak.generators.langchain.html#garak.generators.langchain.LangChainLLMGenerator)  
* [garak.generators.langchain\_serve](https://reference.garak.ai/en/latest/garak.generators.langchain_serve.html)  
  * [`LangChainServeLLMGenerator`](https://reference.garak.ai/en/latest/garak.generators.langchain_serve.html#garak.generators.langchain_serve.LangChainServeLLMGenerator)  
* [garak.generators.litellm](https://reference.garak.ai/en/latest/garak.generators.litellm.html)  
  * [}](https://reference.garak.ai/en/latest/garak.generators.litellm.html#id5)  
  * [`LiteLLMGenerator`](https://reference.garak.ai/en/latest/garak.generators.litellm.html#garak.generators.litellm.LiteLLMGenerator)  
* [garak.generators.octo](https://reference.garak.ai/en/latest/garak.generators.octo.html)  
  * [`InferenceEndpoint`](https://reference.garak.ai/en/latest/garak.generators.octo.html#garak.generators.octo.InferenceEndpoint)  
  * [`OctoGenerator`](https://reference.garak.ai/en/latest/garak.generators.octo.html#garak.generators.octo.OctoGenerator)  
* [garak.generators.ollama](https://reference.garak.ai/en/latest/garak.generators.ollama.html)  
  * [`OllamaGenerator`](https://reference.garak.ai/en/latest/garak.generators.ollama.html#garak.generators.ollama.OllamaGenerator)  
  * [`OllamaGeneratorChat`](https://reference.garak.ai/en/latest/garak.generators.ollama.html#garak.generators.ollama.OllamaGeneratorChat)  
* [garak.generators.openai](https://reference.garak.ai/en/latest/garak.generators.openai.html)  
  * [`OpenAICompatible`](https://reference.garak.ai/en/latest/garak.generators.openai.html#garak.generators.openai.OpenAICompatible)  
  * [`OpenAIGenerator`](https://reference.garak.ai/en/latest/garak.generators.openai.html#garak.generators.openai.OpenAIGenerator)  
  * [`OpenAIReasoningGenerator`](https://reference.garak.ai/en/latest/garak.generators.openai.html#garak.generators.openai.OpenAIReasoningGenerator)  
* [garak.generators.nemo](https://reference.garak.ai/en/latest/garak.generators.nemo.html)  
  * [`NeMoGenerator`](https://reference.garak.ai/en/latest/garak.generators.nemo.html#garak.generators.nemo.NeMoGenerator)  
* [garak.generators.nim](https://reference.garak.ai/en/latest/garak.generators.nim.html)  
  * [`NVOpenAIChat`](https://reference.garak.ai/en/latest/garak.generators.nim.html#garak.generators.nim.NVOpenAIChat)  
  * [`NVOpenAICompletion`](https://reference.garak.ai/en/latest/garak.generators.nim.html#garak.generators.nim.NVOpenAICompletion)  
  * [`Vision`](https://reference.garak.ai/en/latest/garak.generators.nim.html#garak.generators.nim.Vision)  
* [garak.generators.nvcf](https://reference.garak.ai/en/latest/garak.generators.nvcf.html)  
  * [Configuration](https://reference.garak.ai/en/latest/garak.generators.nvcf.html#configuration)  
  * [Scaling](https://reference.garak.ai/en/latest/garak.generators.nvcf.html#scaling)  
* [garak.generators.replicate](https://reference.garak.ai/en/latest/garak.generators.replicate.html)  
  * [`InferenceEndpoint`](https://reference.garak.ai/en/latest/garak.generators.replicate.html#garak.generators.replicate.InferenceEndpoint)  
  * [`ReplicateGenerator`](https://reference.garak.ai/en/latest/garak.generators.replicate.html#garak.generators.replicate.ReplicateGenerator)  
* [garak.generators.rest](https://reference.garak.ai/en/latest/garak.generators.rest.html)  
  * [`RestGenerator`](https://reference.garak.ai/en/latest/garak.generators.rest.html#garak.generators.rest.RestGenerator)  
* [garak.generators.rasa](https://reference.garak.ai/en/latest/garak.generators.rasa.html)  
  * [`RasaRestGenerator`](https://reference.garak.ai/en/latest/garak.generators.rasa.html#garak.generators.rasa.RasaRestGenerator)  
* [garak.generators.test](https://reference.garak.ai/en/latest/garak.generators.test.html)  
  * [`Blank`](https://reference.garak.ai/en/latest/garak.generators.test.html#garak.generators.test.Blank)  
  * [`Lipsum`](https://reference.garak.ai/en/latest/garak.generators.test.html#garak.generators.test.Lipsum)  
  * [`Repeat`](https://reference.garak.ai/en/latest/garak.generators.test.html#garak.generators.test.Repeat)  
  * [`Single`](https://reference.garak.ai/en/latest/garak.generators.test.html#garak.generators.test.Single)  
* [garak.generators.watsonx](https://reference.garak.ai/en/latest/garak.generators.watsonx.html)  
  * [`WatsonXGenerator`](https://reference.garak.ai/en/latest/garak.generators.watsonx.html#garak.generators.watsonx.WatsonXGenerator)

## **garak.harnesses**

* [garak.harnesses](https://reference.garak.ai/en/latest/garak.harnesses.html)  
* [garak.harnesses.base](https://reference.garak.ai/en/latest/garak.harnesses.base.html)  
  * [`Harness`](https://reference.garak.ai/en/latest/garak.harnesses.base.html#garak.harnesses.base.Harness)  
* [garak.harnesses.probewise](https://reference.garak.ai/en/latest/garak.harnesses.probewise.html)  
  * [`ProbewiseHarness`](https://reference.garak.ai/en/latest/garak.harnesses.probewise.html#garak.harnesses.probewise.ProbewiseHarness)  
* [garak.harnesses.pxd](https://reference.garak.ai/en/latest/garak.harnesses.pxd.html)  
  * [`PxD`](https://reference.garak.ai/en/latest/garak.harnesses.pxd.html#garak.harnesses.pxd.PxD)

## **garak.probes**

garak’s probes each define a number of ways of testing a generator (typically an LLM) for a specific vulnerability or failure mode.

For a detailed oversight into how a probe operates, see garak.probes.base.rst.

* [garak.probes](https://reference.garak.ai/en/latest/garak.probes.html)  
* [garak.probes.base](https://reference.garak.ai/en/latest/garak.probes.base.html)  
  * [`Probe`](https://reference.garak.ai/en/latest/garak.probes.base.html#garak.probes.base.Probe)  
  * [`TreeSearchProbe`](https://reference.garak.ai/en/latest/garak.probes.base.html#garak.probes.base.TreeSearchProbe)  
* [garak.probes.continuation](https://reference.garak.ai/en/latest/garak.probes.ansiescape.html)  
  * [`ContinueSlursReclaimedSlurs`](https://reference.garak.ai/en/latest/garak.probes.ansiescape.html#garak.probes.continuation.ContinueSlursReclaimedSlurs)  
  * [`ContinueSlursReclaimedSlursFull`](https://reference.garak.ai/en/latest/garak.probes.ansiescape.html#garak.probes.continuation.ContinueSlursReclaimedSlursFull)  
* [garak.probes.atkgen](https://reference.garak.ai/en/latest/garak.probes.atkgen.html)  
  * [`Tox`](https://reference.garak.ai/en/latest/garak.probes.atkgen.html#garak.probes.atkgen.Tox)  
* [garak.probes.av\_spam\_scanning](https://reference.garak.ai/en/latest/garak.probes.av_spam_scanning.html)  
  * [`EICAR`](https://reference.garak.ai/en/latest/garak.probes.av_spam_scanning.html#garak.probes.av_spam_scanning.EICAR)  
  * [`GTUBE`](https://reference.garak.ai/en/latest/garak.probes.av_spam_scanning.html#garak.probes.av_spam_scanning.GTUBE)  
  * [`GTphish`](https://reference.garak.ai/en/latest/garak.probes.av_spam_scanning.html#garak.probes.av_spam_scanning.GTphish)  
* [garak.probes.continuation](https://reference.garak.ai/en/latest/garak.probes.continuation.html)  
  * [`ContinueSlursReclaimedSlurs`](https://reference.garak.ai/en/latest/garak.probes.continuation.html#garak.probes.continuation.ContinueSlursReclaimedSlurs)  
  * [`ContinueSlursReclaimedSlursFull`](https://reference.garak.ai/en/latest/garak.probes.continuation.html#garak.probes.continuation.ContinueSlursReclaimedSlursFull)  
* [garak.probes.dan](https://reference.garak.ai/en/latest/garak.probes.dan.html)  
  * [`Ablation_Dan_11_0`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.Ablation_Dan_11_0)  
  * [`AntiDAN`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.AntiDAN)  
  * [`AutoDAN`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.AutoDAN)  
  * [`AutoDANCached`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.AutoDANCached)  
  * [`ChatGPT_Developer_Mode_RANTI`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.ChatGPT_Developer_Mode_RANTI)  
  * [`ChatGPT_Developer_Mode_v2`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.ChatGPT_Developer_Mode_v2)  
  * [`ChatGPT_Image_Markdown`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.ChatGPT_Image_Markdown)  
  * [`DAN_Jailbreak`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.DAN_Jailbreak)  
  * [`DUDE`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.DUDE)  
  * [`DanInTheWild`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.DanInTheWild)  
  * [`DanInTheWildFull`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.DanInTheWildFull)  
  * [`Dan_10_0`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.Dan_10_0)  
  * [`Dan_11_0`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.Dan_11_0)  
  * [`Dan_6_0`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.Dan_6_0)  
  * [`Dan_6_2`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.Dan_6_2)  
  * [`Dan_7_0`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.Dan_7_0)  
  * [`Dan_8_0`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.Dan_8_0)  
  * [`Dan_9_0`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.Dan_9_0)  
  * [`STAN`](https://reference.garak.ai/en/latest/garak.probes.dan.html#garak.probes.dan.STAN)  
* [garak.probes.divergence](https://reference.garak.ai/en/latest/garak.probes.divergence.html)  
  * [`Repeat`](https://reference.garak.ai/en/latest/garak.probes.divergence.html#garak.probes.divergence.Repeat)  
  * [`RepeatExtended`](https://reference.garak.ai/en/latest/garak.probes.divergence.html#garak.probes.divergence.RepeatExtended)  
* [garak.probes.donotanswer](https://reference.garak.ai/en/latest/garak.probes.donotanswer.html)  
  * [`DiscriminationExclusionToxicityHatefulOffensive`](https://reference.garak.ai/en/latest/garak.probes.donotanswer.html#garak.probes.donotanswer.DiscriminationExclusionToxicityHatefulOffensive)  
  * [`HumanChatbox`](https://reference.garak.ai/en/latest/garak.probes.donotanswer.html#garak.probes.donotanswer.HumanChatbox)  
  * [`InformationHazard`](https://reference.garak.ai/en/latest/garak.probes.donotanswer.html#garak.probes.donotanswer.InformationHazard)  
  * [`MaliciousUses`](https://reference.garak.ai/en/latest/garak.probes.donotanswer.html#garak.probes.donotanswer.MaliciousUses)  
  * [`MisinformationHarms`](https://reference.garak.ai/en/latest/garak.probes.donotanswer.html#garak.probes.donotanswer.MisinformationHarms)  
  * [`load_local_data()`](https://reference.garak.ai/en/latest/garak.probes.donotanswer.html#garak.probes.donotanswer.load_local_data)  
  * [`local_constructor()`](https://reference.garak.ai/en/latest/garak.probes.donotanswer.html#garak.probes.donotanswer.local_constructor)  
* [garak.probes.encoding](https://reference.garak.ai/en/latest/garak.probes.encoding.html)  
  * [`BaseEncodingProbe`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.BaseEncodingProbe)  
  * [`InjectAscii85`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectAscii85)  
  * [`InjectBase16`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectBase16)  
  * [`InjectBase2048`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectBase2048)  
  * [`InjectBase32`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectBase32)  
  * [`InjectBase64`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectBase64)  
  * [`InjectBraille`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectBraille)  
  * [`InjectEcoji`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectEcoji)  
  * [`InjectHex`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectHex)  
  * [`InjectMime`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectMime)  
  * [`InjectMorse`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectMorse)  
  * [`InjectNato`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectNato)  
  * [`InjectQP`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectQP)  
  * [`InjectROT13`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectROT13)  
  * [`InjectUU`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectUU)  
  * [`InjectZalgo`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.InjectZalgo)  
  * [`braille()`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.braille)  
  * [`morse()`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.morse)  
  * [`rot13()`](https://reference.garak.ai/en/latest/garak.probes.encoding.html#garak.probes.encoding.rot13)  
* [garak.probes.fileformats](https://reference.garak.ai/en/latest/garak.probes.fileformats.html)  
  * [`HF_Files`](https://reference.garak.ai/en/latest/garak.probes.fileformats.html#garak.probes.fileformats.HF_Files)  
* [garak.probes.glitch](https://reference.garak.ai/en/latest/garak.probes.glitch.html)  
  * [`Glitch`](https://reference.garak.ai/en/latest/garak.probes.glitch.html#garak.probes.glitch.Glitch)  
  * [`GlitchFull`](https://reference.garak.ai/en/latest/garak.probes.glitch.html#garak.probes.glitch.GlitchFull)  
* [garak.probes.goodside](https://reference.garak.ai/en/latest/garak.probes.goodside.html)  
  * [`Davidjl`](https://reference.garak.ai/en/latest/garak.probes.goodside.html#garak.probes.goodside.Davidjl)  
  * [`Tag`](https://reference.garak.ai/en/latest/garak.probes.goodside.html#garak.probes.goodside.Tag)  
  * [`ThreatenJSON`](https://reference.garak.ai/en/latest/garak.probes.goodside.html#garak.probes.goodside.ThreatenJSON)  
  * [`WhoIsRiley`](https://reference.garak.ai/en/latest/garak.probes.goodside.html#garak.probes.goodside.WhoIsRiley)  
* [garak.probes.grandma](https://reference.garak.ai/en/latest/garak.probes.grandma.html)  
  * [`Slurs`](https://reference.garak.ai/en/latest/garak.probes.grandma.html#garak.probes.grandma.Slurs)  
  * [`Substances`](https://reference.garak.ai/en/latest/garak.probes.grandma.html#garak.probes.grandma.Substances)  
  * [`Win10`](https://reference.garak.ai/en/latest/garak.probes.grandma.html#garak.probes.grandma.Win10)  
  * [`Win11`](https://reference.garak.ai/en/latest/garak.probes.grandma.html#garak.probes.grandma.Win11)  
* [garak.probes.latentinjection](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html)  
  * [`LatentInjectionFactSnippetEiffel`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionFactSnippetEiffel)  
  * [`LatentInjectionFactSnippetEiffelFull`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionFactSnippetEiffelFull)  
  * [`LatentInjectionFactSnippetLegal`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionFactSnippetLegal)  
  * [`LatentInjectionFactSnippetLegalFull`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionFactSnippetLegalFull)  
  * [`LatentInjectionMixin`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionMixin)  
  * [`LatentInjectionReport`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionReport)  
  * [`LatentInjectionReportFull`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionReportFull)  
  * [`LatentInjectionResume`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionResume)  
  * [`LatentInjectionResumeFull`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionResumeFull)  
  * [`LatentInjectionTranslationEnFr`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionTranslationEnFr)  
  * [`LatentInjectionTranslationEnFrFull`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionTranslationEnFrFull)  
  * [`LatentInjectionTranslationEnZh`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionTranslationEnZh)  
  * [`LatentInjectionTranslationEnZhFull`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentInjectionTranslationEnZhFull)  
  * [`LatentJailbreak`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentJailbreak)  
  * [`LatentJailbreakFull`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentJailbreakFull)  
  * [`LatentWhois`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentWhois)  
  * [`LatentWhoisSnippet`](https://reference.garak.ai/en/latest/garak.probes.latentinjection.html#garak.probes.latentinjection.LatentWhoisSnippet)  
* [garak.probes.leakreplay](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html)  
  * [`GuardianCloze`](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html#garak.probes.leakreplay.GuardianCloze)  
  * [`GuardianComplete`](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html#garak.probes.leakreplay.GuardianComplete)  
  * [`LiteratureCloze`](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html#garak.probes.leakreplay.LiteratureCloze)  
  * [`LiteratureClozeFull`](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html#garak.probes.leakreplay.LiteratureClozeFull)  
  * [`LiteratureComplete`](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html#garak.probes.leakreplay.LiteratureComplete)  
  * [`LiteratureCompleteFull`](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html#garak.probes.leakreplay.LiteratureCompleteFull)  
  * [`NYTCloze`](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html#garak.probes.leakreplay.NYTCloze)  
  * [`NYTComplete`](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html#garak.probes.leakreplay.NYTComplete)  
  * [`PotterCloze`](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html#garak.probes.leakreplay.PotterCloze)  
  * [`PotterComplete`](https://reference.garak.ai/en/latest/garak.probes.leakreplay.html#garak.probes.leakreplay.PotterComplete)  
* [garak.probes.lmrc](https://reference.garak.ai/en/latest/garak.probes.lmrc.html)  
  * [`Anthropomorphisation`](https://reference.garak.ai/en/latest/garak.probes.lmrc.html#garak.probes.lmrc.Anthropomorphisation)  
  * [`Bullying`](https://reference.garak.ai/en/latest/garak.probes.lmrc.html#garak.probes.lmrc.Bullying)  
  * [`Deadnaming`](https://reference.garak.ai/en/latest/garak.probes.lmrc.html#garak.probes.lmrc.Deadnaming)  
  * [`Profanity`](https://reference.garak.ai/en/latest/garak.probes.lmrc.html#garak.probes.lmrc.Profanity)  
  * [`QuackMedicine`](https://reference.garak.ai/en/latest/garak.probes.lmrc.html#garak.probes.lmrc.QuackMedicine)  
  * [`SexualContent`](https://reference.garak.ai/en/latest/garak.probes.lmrc.html#garak.probes.lmrc.SexualContent)  
  * [`Sexualisation`](https://reference.garak.ai/en/latest/garak.probes.lmrc.html#garak.probes.lmrc.Sexualisation)  
  * [`SlurUsage`](https://reference.garak.ai/en/latest/garak.probes.lmrc.html#garak.probes.lmrc.SlurUsage)  
* [garak.probes.malwaregen](https://reference.garak.ai/en/latest/garak.probes.malwaregen.html)  
  * [`Evasion`](https://reference.garak.ai/en/latest/garak.probes.malwaregen.html#garak.probes.malwaregen.Evasion)  
  * [`Payload`](https://reference.garak.ai/en/latest/garak.probes.malwaregen.html#garak.probes.malwaregen.Payload)  
  * [`SubFunctions`](https://reference.garak.ai/en/latest/garak.probes.malwaregen.html#garak.probes.malwaregen.SubFunctions)  
  * [`TopLevel`](https://reference.garak.ai/en/latest/garak.probes.malwaregen.html#garak.probes.malwaregen.TopLevel)  
* [garak.probes.misleading](https://reference.garak.ai/en/latest/garak.probes.misleading.html)  
  * [`FalseAssertion`](https://reference.garak.ai/en/latest/garak.probes.misleading.html#garak.probes.misleading.FalseAssertion)  
* [garak.probes.packagehallucination](https://reference.garak.ai/en/latest/garak.probes.packagehallucination.html)  
  * [`JavaScript`](https://reference.garak.ai/en/latest/garak.probes.packagehallucination.html#garak.probes.packagehallucination.JavaScript)  
  * [`PackageHallucinationProbe`](https://reference.garak.ai/en/latest/garak.probes.packagehallucination.html#garak.probes.packagehallucination.PackageHallucinationProbe)  
  * [`Python`](https://reference.garak.ai/en/latest/garak.probes.packagehallucination.html#garak.probes.packagehallucination.Python)  
  * [`Ruby`](https://reference.garak.ai/en/latest/garak.probes.packagehallucination.html#garak.probes.packagehallucination.Ruby)  
  * [`Rust`](https://reference.garak.ai/en/latest/garak.probes.packagehallucination.html#garak.probes.packagehallucination.Rust)  
* [garak.probes.phrasing](https://reference.garak.ai/en/latest/garak.probes.phrasing.html)  
  * [`FutureTense`](https://reference.garak.ai/en/latest/garak.probes.phrasing.html#garak.probes.phrasing.FutureTense)  
  * [`FutureTenseFull`](https://reference.garak.ai/en/latest/garak.probes.phrasing.html#garak.probes.phrasing.FutureTenseFull)  
  * [`PastTense`](https://reference.garak.ai/en/latest/garak.probes.phrasing.html#garak.probes.phrasing.PastTense)  
  * [`PastTenseFull`](https://reference.garak.ai/en/latest/garak.probes.phrasing.html#garak.probes.phrasing.PastTenseFull)  
* [garak.probes.promptinject](https://reference.garak.ai/en/latest/garak.probes.promptinject.html)  
  * [`HijackHateHumans`](https://reference.garak.ai/en/latest/garak.probes.promptinject.html#garak.probes.promptinject.HijackHateHumans)  
  * [`HijackHateHumansFull`](https://reference.garak.ai/en/latest/garak.probes.promptinject.html#garak.probes.promptinject.HijackHateHumansFull)  
  * [`HijackKillHumans`](https://reference.garak.ai/en/latest/garak.probes.promptinject.html#garak.probes.promptinject.HijackKillHumans)  
  * [`HijackKillHumansFull`](https://reference.garak.ai/en/latest/garak.probes.promptinject.html#garak.probes.promptinject.HijackKillHumansFull)  
  * [`HijackLongPrompt`](https://reference.garak.ai/en/latest/garak.probes.promptinject.html#garak.probes.promptinject.HijackLongPrompt)  
  * [`HijackLongPromptFull`](https://reference.garak.ai/en/latest/garak.probes.promptinject.html#garak.probes.promptinject.HijackLongPromptFull)  
  * [`constructor()`](https://reference.garak.ai/en/latest/garak.probes.promptinject.html#garak.probes.promptinject.constructor)  
  * [`load_data_all_attacks()`](https://reference.garak.ai/en/latest/garak.probes.promptinject.html#garak.probes.promptinject.load_data_all_attacks)  
* [garak.probes.realtoxicityprompts](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html)  
  * [`RTPBlank`](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html#garak.probes.realtoxicityprompts.RTPBlank)  
  * [`RTPFlirtation`](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html#garak.probes.realtoxicityprompts.RTPFlirtation)  
  * [`RTPIdentity_Attack`](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html#garak.probes.realtoxicityprompts.RTPIdentity_Attack)  
  * [`RTPInsult`](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html#garak.probes.realtoxicityprompts.RTPInsult)  
  * [`RTPProfanity`](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html#garak.probes.realtoxicityprompts.RTPProfanity)  
  * [`RTPSevere_Toxicity`](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html#garak.probes.realtoxicityprompts.RTPSevere_Toxicity)  
  * [`RTPSexually_Explicit`](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html#garak.probes.realtoxicityprompts.RTPSexually_Explicit)  
  * [`RTPThreat`](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html#garak.probes.realtoxicityprompts.RTPThreat)  
  * [`load_local_data()`](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html#garak.probes.realtoxicityprompts.load_local_data)  
  * [`local_constructor()`](https://reference.garak.ai/en/latest/garak.probes.realtoxicityprompts.html#garak.probes.realtoxicityprompts.local_constructor)  
* [garak.probes.snowball](https://reference.garak.ai/en/latest/garak.probes.snowball.html)  
  * [`GraphConnectivity`](https://reference.garak.ai/en/latest/garak.probes.snowball.html#garak.probes.snowball.GraphConnectivity)  
  * [`GraphConnectivityFull`](https://reference.garak.ai/en/latest/garak.probes.snowball.html#garak.probes.snowball.GraphConnectivityFull)  
  * [`Primes`](https://reference.garak.ai/en/latest/garak.probes.snowball.html#garak.probes.snowball.Primes)  
  * [`PrimesFull`](https://reference.garak.ai/en/latest/garak.probes.snowball.html#garak.probes.snowball.PrimesFull)  
  * [`Senators`](https://reference.garak.ai/en/latest/garak.probes.snowball.html#garak.probes.snowball.Senators)  
  * [`SenatorsFull`](https://reference.garak.ai/en/latest/garak.probes.snowball.html#garak.probes.snowball.SenatorsFull)  
* [garak.probes.suffix](https://reference.garak.ai/en/latest/garak.probes.suffix.html)  
  * [`BEAST`](https://reference.garak.ai/en/latest/garak.probes.suffix.html#garak.probes.suffix.BEAST)  
  * [`GCG`](https://reference.garak.ai/en/latest/garak.probes.suffix.html#garak.probes.suffix.GCG)  
  * [`GCGCached`](https://reference.garak.ai/en/latest/garak.probes.suffix.html#garak.probes.suffix.GCGCached)  
* [garak.probes.tap](https://reference.garak.ai/en/latest/garak.probes.tap.html)  
  * [`PAIR`](https://reference.garak.ai/en/latest/garak.probes.tap.html#garak.probes.tap.PAIR)  
  * [`TAP`](https://reference.garak.ai/en/latest/garak.probes.tap.html#garak.probes.tap.TAP)  
  * [`TAPCached`](https://reference.garak.ai/en/latest/garak.probes.tap.html#garak.probes.tap.TAPCached)  
* [garak.probes.test](https://reference.garak.ai/en/latest/garak.probes.test.html)  
  * [`Blank`](https://reference.garak.ai/en/latest/garak.probes.test.html#garak.probes.test.Blank)  
  * [`Test`](https://reference.garak.ai/en/latest/garak.probes.test.html#garak.probes.test.Test)  
* [garak.probes.topic](https://reference.garak.ai/en/latest/garak.probes.topic.html)  
  * [`WordnetAllowedWords`](https://reference.garak.ai/en/latest/garak.probes.topic.html#garak.probes.topic.WordnetAllowedWords)  
  * [`WordnetBlockedWords`](https://reference.garak.ai/en/latest/garak.probes.topic.html#garak.probes.topic.WordnetBlockedWords)  
  * [`WordnetControversial`](https://reference.garak.ai/en/latest/garak.probes.topic.html#garak.probes.topic.WordnetControversial)  
* [garak.probes.xss](https://reference.garak.ai/en/latest/garak.probes.xss.html)  
  * [`ColabAIDataLeakage`](https://reference.garak.ai/en/latest/garak.probes.xss.html#garak.probes.xss.ColabAIDataLeakage)  
  * [`MarkdownImageExfil`](https://reference.garak.ai/en/latest/garak.probes.xss.html#garak.probes.xss.MarkdownImageExfil)  
  * [`MdExfil20230929`](https://reference.garak.ai/en/latest/garak.probes.xss.html#garak.probes.xss.MdExfil20230929)  
  * [`StringAssemblyDataExfil`](https://reference.garak.ai/en/latest/garak.probes.xss.html#garak.probes.xss.StringAssemblyDataExfil)  
* [garak.probes.visual\_jailbreak](https://reference.garak.ai/en/latest/garak.probes.visual_jailbreak.html)  
  * [`FigStep`](https://reference.garak.ai/en/latest/garak.probes.visual_jailbreak.html#garak.probes.visual_jailbreak.FigStep)  
  * [`FigStepFull`](https://reference.garak.ai/en/latest/garak.probes.visual_jailbreak.html#garak.probes.visual_jailbreak.FigStepFull)

## **garak.report**

`garak`’s reports connect to things interested in consuming info on LLM vulnerabilities and failures, such as the AI Vulnerability Database.

`garak` provides a CLI option to further structure this file for downstream consumption. The open data schema of AI vulnerability Database ([AVID](https://avidml.org)) is used for this purpose.

The syntax for this is as follows:

python3 \-m garak \-r \<path\_to\_file\>

### **Examples**

As an example, let’s load up a `garak` report from scanning `gpt-3.5-turbo-0613`.

wget https://gist.githubusercontent.com/shubhobm/9fa52d71c8bb36bfb888eee2ba3d18f2/raw/ef1808e6d3b26002d9b046e6c120d438adf49008/gpt35-0906.report.jsonl  
python3 \-m garak \-r gpt35-0906.report.jsonl

This produces the following output.

📜 Converting garak reports gpt35-0906.report.jsonl  
📜 AVID reports generated at gpt35-0906.avid.jsonl

* [garak.report](https://reference.garak.ai/en/latest/garak.report.html)  
  * [`Report`](https://reference.garak.ai/en/latest/garak.report.html#garak.report.Report)

