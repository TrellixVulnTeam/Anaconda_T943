# Elegans
Elegant 3D plots generator with WebGL.

![alt text](https://dl.dropboxusercontent.com/u/47978121/ss561.png)

## Description
Elegans is a 3D plotting library written in JavaScript. You can generate charts in JavaScript, and show them on your browser.

We began to develop Elegans in order to embed it into other languages like Ruby and Python, so you can embed it into your environments in a relatively simple way. See 'Embed Elegans into your environments' paragraph in 'Usage' below.

Elegans is still in its alpha release, and some charts and options are not implemented yet.
Please see [documents](http://elegans.readthedocs.org) to learn more.

## Demos
| Name | Shortcuts function | Data type | Legend option | Link to examples |
|:---- |:--------- |:--------- |:-----:|:----------------:|
| Elegans.Surface | Elegans.SurfacePlot | Matrix | o | [example](http://bl.ocks.org/domitry/11322618) |
| Elegans.Wireframe | Elegans.WireframePlot | Matrix | o | [example](http://bl.ocks.org/domitry/11392477) |
| Elegans.Line | Elegans.LinePlot | Array | o | [example](http://bl.ocks.org/domitry/11338075) |
| Elegans.Particles | Elegans.ParticlesPlot | Array | o | [example](http://bl.ocks.org/domitry/11322575) |
| Elegans.Scatter | Elegans.ScatterPlot | Array | o | [example](http://bl.ocks.org/domitry/11373451) |

## Usage
### Getting Started
Download latest version of Elegans from [here](https://raw.githubusercontent.com/domitry/elegans/master/release/elegans.min.js). 
And add code below to your html file.

```html:
<script type="text/javascript" src="http://cdnjs.cloudflare.com/ajax/libs/three.js/r66/three.min.js"></script>
<script type="text/javascript" src="http://cdnjs.cloudflare.com/ajax/libs/d3/3.4.4/d3.min.js"></script>
<script type="text/javascript" src="your_link_to_elegans.min.js"></script>
```

### Generating charts with JavaScript

At first you need to create stage, then generate some charts add them to the stage.

```javascript:
var stage = new Elegans.Stage(d3.select(#vis));
var surface = new Elegans.Surface(data);
stage.add(surface);
stage.render();
```

You can generate the same charts more simply, with d3.js selection and method chain style.

```javascript:
d3.select('#vis').datum(data).call(Elegans.SurfacePlot);
```


### Embed Elegans to your environment
Elegans has API to make it easier to embed it into environments except browsers, like IPython notebook.
What you have to do is only to generate simple JSON object, and embed it into static html templates. See below.

```javascript:
var model = {charts:[{type:"Particles",data:{x:[1,2,3],y:[1,2,3],z:[1,2,3]},options:{color:"#000000"}}], options:{width:500, height:500}};
Elegans.Embed.parse(model, "#vis");
```

If you need more information, see [documents](http://elegans.readthedocs.org).

## Build Elegans
At first, pull repository from github.

```shell:
git pull https://github.com/domitry/elegans.git
```

You need to install npm with node.js before building Elegans. You can build it by running commands below.


```shell:
cd elegans
npm install
grunt release
```

## Supported browsers
We are checking if Elegans works well on two browsers.
* Google Chrome: Latest version
* Firefox: Latest version

## Dependency
* d3.js version 3.4.4
* three.js version r66

## License
Copyright (C) 2014 by Naoki Nishida  
This version of Elegans is licensed under the MIT license.
