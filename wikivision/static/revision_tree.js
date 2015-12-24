function nestNodeList(nodes) {
  var nodeById = {};

  // Index the nodes by id, in case they come out of order.
  nodes.forEach(function(d) {
    nodeById[d.wikitext_version] = d;
  });

  // Lazily compute children.
  nodes.forEach(function(d) {
    if ("wikitext_parent_version" in d) {
      var parent = nodeById[d.wikitext_parent_version];
      if (parent.children) parent.children.push(d);
      else parent.children = [d];
    }
  });

  return nodes[0];
}

function revisionTree(root) {
  var i = 0;

  // Compute the new tree layout.
  var nodes = tree.nodes(root).reverse(),
	    links = tree.links(nodes);

  // Normalize for fixed-depth.
  nodes.forEach(function(d) { d.y = d.depth * 100; });

  // Declare the nodes…
  var node = svg.selectAll("g.node")
	  .data(nodes, function(d) { return d.id || (d.id = ++i); });

  // Enter the nodes.
  var nodeEnter = node.enter().append("g")
	  .attr("class", "node")
	  .attr("transform", function(d) {
		  return "translate(" + d.x + "," + d.y + ")"; });

  nodeEnter.append("circle")
	  .attr("r", 10)
	  .style("fill", "#fff");

  nodeEnter.append("text")
	  .attr("y", function(d) {
		  return d.children || d._children ? -18 : 18; })
	  .attr("dy", ".35em")
	  .attr("text-anchor", "middle")
	  .text(function(d) { return d.wikitext; })
	  .style("fill-opacity", 1);

  // Declare the links…
  var link = svg.selectAll("path.link")
	  .data(links, function(d) { return d.target.id; });

  // Enter the links.
  link.enter().insert("path", "g")
	  .attr("class", "link")
	  .attr("d", diagonal);

}
