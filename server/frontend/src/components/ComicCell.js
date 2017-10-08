/**
 * Created by Ornithopter on 2017/10/8.
 */
import React from "react";
import {List, ListItem} from "material-ui/List";

class ComicCell extends React.Component {
    constructor(props) {
        super(props);
    }

    render() {
        return <ListItem primaryText={this.props.title} secondaryText={this.props.author}/>
    }
}

export default ComicCell;